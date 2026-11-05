"""注文・配送・キャンセル承認（生産者）のView

対象API:
  GET   /api/v1/dashboard/orders
  GET   /api/v1/dashboard/orders/<order_id>
  PATCH /api/v1/dashboard/orders/<order_id>/shipping
  POST  /api/v1/dashboard/orders/<order_id>/cancel/approve
  POST  /api/v1/dashboard/orders/<order_id>/cancel/reject

共通ルール:
  - ログイン中で承認済みの生産者だけ利用できる
  - 自分の配送箱と明細だけ取得できる
  - 注文一覧は支払い済み（paid）の注文だけ
  - 発送登録は unshipped の場合だけ可能
  - キャンセル承認は cancel_requested の場合だけ可能
  - キャンセル承認時は在庫を戻す
  - キャンセル拒否時は unshipped に戻す
  - 掲載停止中でも注文管理は可能
"""

import hashlib

import stripe

from django.conf import settings
from django.db import transaction
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import APIException, NotFound

from marche.models import Order, OrderShipment, Product

from api.common.permissions import IsApprovedProducer

from api.serializers.dashboard.orders import (
    DashboardOrderListQuerySerializer,
    DashboardOrderListItemSerializer,
    DashboardOrderListResponseSerializer,
    DashboardOrderDetailSerializer,
    DashboardOrderShippingSerializer,
)


# 共通処理
class OrderConflict(APIException):
    """注文・配送の状態が不正な場合の409エラー"""

    status_code = status.HTTP_409_CONFLICT
    default_detail = "現在の状態ではこの操作を実行できません。"
    default_code = "ORDER_STATE_CONFLICT"


def get_producer(request):
    """ログイン中のユーザーに紐づく生産者を取得する"""

    try:
        return request.user.producer
    except Exception:
        raise NotFound("生産者情報が見つかりません。")


def get_producer_order_queryset(producer):
    """自分の配送箱がある注文だけを取得する"""

    return (
        Order.objects
        .filter(
            payment_status="paid",
            order_shipments__producer=producer,
        )
        .distinct()
        .prefetch_related(
            "order_shipments__order_items",
        )
        .order_by("-ordered_at", "-id")
    )


def get_shipment_etags(shipments):
    """配送箱の更新日時からETagを生成する"""

    etags = {}

    for shipment in shipments:
        updated_at = shipment.updated_at.isoformat()

        digest = hashlib.sha256(
            f"{shipment.id}:{updated_at}".encode()
        ).hexdigest()

        etags[shipment.id] = f'"{digest}"'

    return etags


def get_order_serializer_context(request, producer, order):
    """注文シリアライザーに渡す共通情報"""

    shipments = list(
        order.order_shipments.filter(
            producer=producer
        ).prefetch_related(
            "order_items"
        )
    )

    return {
        "request": request,
        "producer": producer,
        "shipment_etags": get_shipment_etags(shipments),
    }


# 注文一覧
# GET /api/v1/dashboard/orders
class DashboardOrderListView(APIView):
    """生産者向け注文一覧"""

    permission_classes = [IsApprovedProducer]

    def get(self, request):

        producer = get_producer(request)

        # クエリパラメータを検証
        query_serializer = DashboardOrderListQuerySerializer(
            data=request.query_params
        )

        query_serializer.is_valid(raise_exception=True)

        page = query_serializer.validated_data["page"]
        page_size = query_serializer.validated_data["page_size"]

        # 自分の配送箱がある支払い済み注文だけ取得
        queryset = get_producer_order_queryset(producer)

        total = queryset.count()

        total_pages = (
            (total + page_size - 1) // page_size
        )

        start = (page - 1) * page_size
        end = start + page_size

        orders = list(queryset[start:end])

        # 配送箱のETagを作成
        shipment_etags = {}

        for order in orders:
            shipments = order.order_shipments.filter(
                producer=producer
            )

            shipment_etags.update(
                get_shipment_etags(shipments)
            )

        # 注文一覧をシリアライズ
        context = {
            "request": request,
            "producer": producer,
            "shipment_etags": shipment_etags,
        }

        items = DashboardOrderListItemSerializer(
            orders,
            many=True,
            context=context,
        ).data

        response_data = {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

        response_serializer = DashboardOrderListResponseSerializer(
            response_data
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_200_OK,
        )


# 注文詳細
# GET /api/v1/dashboard/orders/<order_id>
class DashboardOrderDetailView(APIView):
    """生産者向け注文詳細"""

    permission_classes = [IsApprovedProducer]

    def get(self, request, order_id):

        producer = get_producer(request)

        # 自分の配送箱が存在する支払い済み注文だけ取得
        order = get_object_or_404(
            get_producer_order_queryset(producer),
            pk=order_id,
        )

        context = get_order_serializer_context(
            request,
            producer,
            order,
        )

        serializer = DashboardOrderDetailSerializer(
            order,
            context=context,
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


# 発送登録
# PATCH /api/v1/dashboard/orders/<order_id>/shipping
class DashboardOrderShippingView(APIView):
    """生産者による発送登録"""

    permission_classes = [IsApprovedProducer]

    def patch(self, request, order_id):

        producer = get_producer(request)

        # 入力値の検証
        serializer = DashboardOrderShippingSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        shipment_id = serializer.validated_data["shipment_id"]

        tracking_no = serializer.validated_data.get("tracking_no")

        with transaction.atomic():

            # 自分の配送箱だけ取得してロック
            shipment = get_object_or_404(
                OrderShipment.objects
                .select_for_update()
                .filter(
                    order_id=order_id,
                    producer=producer,
                ),
                pk=shipment_id,
            )

            # 未発送の箱だけ発送できる
            if shipment.status != "unshipped":
                raise OrderConflict(
                    "この配送箱は発送登録できる状態ではありません。"
                )

            # 発送情報を更新
            shipment.status = "shipped"
            shipment.tracking_no = tracking_no
            shipment.shipped_at = timezone.now()

            shipment.save(
                update_fields=[
                    "status",
                    "tracking_no",
                    "shipped_at",
                    "updated_at",
                ]
            )

        return Response(
            {
                "message": "発送登録が完了しました。",
                "order_id": order_id,
                "shipment_id": shipment.id,
                "status": shipment.status,
            },
            status=status.HTTP_200_OK,
        )


# キャンセル承認
# POST /api/v1/dashboard/orders/<order_id>/cancel/approve
class DashboardOrderCancelApproveView(APIView):
    """生産者によるキャンセル承認"""

    permission_classes = [IsApprovedProducer]

    def post(self, request, order_id):

        producer = get_producer(request)

        with transaction.atomic():

            # 対象注文に属する自分のキャンセル申請箱をロック
            shipments = list(
                OrderShipment.objects
                .select_for_update()
                .filter(
                    order_id=order_id,
                    producer=producer,
                    status="cancel_requested",
                )
            )

            if not shipments:
                raise OrderConflict(
                    "承認できるキャンセル申請がありません。"
                )

            # 注文を取得
            order = get_object_or_404(
                Order,
                pk=order_id,
                payment_status="paid",
            )

            canceled_shipment_ids = []

            for shipment in shipments:

                # 明細を取得
                order_items = shipment.order_items.select_related(
                    "product"
                )

                # 在庫を復元
                for item in order_items:

                    product = Product.objects.select_for_update().get(
                        pk=item.product_id
                    )

                    # stock が NULL の商品は在庫管理対象外
                    if product.stock is not None:

                        product.stock += item.quantity

                        product.save(
                            update_fields=[
                                "stock",
                                "updated_at",
                            ]
                        )

                # キャンセル確定
                shipment.status = "canceled"
                shipment.canceled_at = timezone.now()

                shipment.save(
                    update_fields=[
                        "status",
                        "canceled_at",
                        "updated_at",
                    ]
                )

                canceled_shipment_ids.append(shipment.id)

            # カード決済の場合は箱ごとに部分返金を試みる
            if order.payment_method == "card":

                stripe_key = getattr(
                    settings,
                    "STRIPE_SECRET_KEY",
                    None,
                )

                if stripe_key and order.stripe_payment_intent_id:

                    stripe.api_key = stripe_key

                    for shipment in shipments:

                        refund_amount = (
                            shipment.order_items.aggregate(
                                total=Sum("subtotal")
                            )["total"] or 0
                        ) + shipment.shipping_fee

                        if refund_amount <= 0:
                            continue

                        try:
                            refund = stripe.Refund.create(
                                payment_intent=order.stripe_payment_intent_id,
                                amount=refund_amount,
                                idempotency_key=(
                                    f"producer-cancel-shipment-{shipment.id}"
                                ),
                            )

                            shipment.stripe_refund_id = refund.id
                            shipment.refunded_amount = refund_amount

                            shipment.save(
                                update_fields=[
                                    "stripe_refund_id",
                                    "refunded_amount",
                                    "updated_at",
                                ]
                            )

                        except stripe.StripeError:
                            # Stripe返金に失敗した場合は返金待ちにする
                            # refunded_amount は NULL のまま
                            continue

        return Response(
            {
                "message": "キャンセルを承認しました。",
                "order_id": order_id,
                "shipment_ids": canceled_shipment_ids,
                "status": "canceled",
            },
            status=status.HTTP_200_OK,
        )


# キャンセル拒否
# POST /api/v1/dashboard/orders/<order_id>/cancel/reject
class DashboardOrderCancelRejectView(APIView):
    """生産者によるキャンセル拒否"""

    permission_classes = [IsApprovedProducer]

    def post(self, request, order_id):

        producer = get_producer(request)

        with transaction.atomic():

            # 自分のキャンセル申請箱だけロック
            shipments = list(
                OrderShipment.objects
                .select_for_update()
                .filter(
                    order_id=order_id,
                    producer=producer,
                    status="cancel_requested",
                )
            )

            if not shipments:
                raise OrderConflict(
                    "拒否できるキャンセル申請がありません。"
                )

            rejected_shipment_ids = []

            for shipment in shipments:

                # キャンセル申請を拒否して未発送に戻す
                shipment.status = "unshipped"

                shipment.save(
                    update_fields=[
                        "status",
                        "updated_at",
                    ]
                )

                rejected_shipment_ids.append(shipment.id)

        return Response(
            {
                "message": "キャンセル申請を拒否しました。",
                "order_id": order_id,
                "shipment_ids": rejected_shipment_ids,
                "status": "unshipped",
            },
            status=status.HTTP_200_OK,
        )


# """注文・配送・キャンセル承認（生産者）

# 認証: 生産者
# 共通: 生産者APIの共通チェック（approved でなければ 403、掲載停止中にできない操作は 409）は common/permissions.py

# このファイルに書くもの（APIView / generics のクラス）。シーケンス図は Notion の同名の図:
#   - 注文一覧（生産者）: GET /api/v1/dashboard/orders
#       ・自分の箱がある paid の注文だけ
#   - 注文詳細（生産者）: GET /api/v1/dashboard/orders/:orderId
#       ・自分の箱と明細、お届け先（ship_*）だけ。他の生産者の箱と購入者のメールは返さない
#   - 発送登録: PATCH /api/v1/dashboard/orders/:orderId/shipping
#       ・shipment_id・tracking_no（任意）。unshipped のときだけ shipped にして shipped_at を入れる。購入者に通知・メール
#   - キャンセル承認: POST /api/v1/dashboard/orders/:orderId/cancel/approve
#       ・自分の箱が cancel_requested のとき。canceled にして在庫を戻す
#       ・カードは Stripe で箱ごとに部分返金 → services/payments.py。コンビニ払い・返金エラーは refunded_amount を空のまま（返金待ち）
#   - キャンセル拒否: POST /api/v1/dashboard/orders/:orderId/cancel/reject
#       ・unshipped に戻す

# 仕様: claude/api-spec.md / カラム名: claude/er-diagram.md
# """
