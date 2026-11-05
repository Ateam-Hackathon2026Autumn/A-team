"""管理者向け注文・返金APIのView

GET  /api/v1/admin/orders
GET  /api/v1/admin/orders/<order_id>
POST /api/v1/admin/orders/<order_id>/cancel
POST /api/v1/admin/orders/<order_id>/refund

CS・管理者グループに所属する運営スタッフが利用する。
"""

from decimal import Decimal

from django.db import transaction
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError, NotFound, APIException

from marche.models import Order, OrderShipment, Product

from api.common.permissions import IsAdminCSOrAdmin
from api.services.audit import record_audit_log

from api.serializers.admin.orders import (
    AdminOrderCancelSerializer,
    AdminOrderRefundSerializer,
    AdminOrderListItemSerializer,
    AdminOrderListResponseSerializer,
    AdminOrderDetailSerializer,
)


class AdminOrderListView(APIView):
    """管理者向け注文一覧"""

    permission_classes = [IsAdminCSOrAdmin]

    def get(self, request):
        """注文一覧を取得する"""

        queryset = (
            Order.objects
            .select_related("user")
            .prefetch_related(
                "order_shipments__order_items"
            )
            .order_by("-ordered_at")
        )

        # キーワード検索（注文番号・メールアドレス）
        keyword = request.query_params.get("keyword")

        if keyword:
            queryset = queryset.filter(
                Q(order_no__icontains=keyword)
                | Q(guest_email__icontains=keyword)
                | Q(user__email__icontains=keyword)
            )

        # 決済ステータス
        payment_status = request.query_params.get("payment_status")

        if payment_status:
            queryset = queryset.filter(
                payment_status=payment_status
            )

        # 箱の配送ステータス
        shipment_status = request.query_params.get("shipment_status")

        if shipment_status:
            queryset = queryset.filter(
                order_shipments__status=shipment_status
            ).distinct()

        # 返金待ちだけを取得
        refund_pending = request.query_params.get("refund_pending")

        if refund_pending == "true":
            queryset = queryset.filter(
                order_shipments__status="canceled",
                order_shipments__refunded_amount__isnull=True,
            ).distinct()

        # 注文日の範囲
        # ※クエリ名はAPI仕様との最終確認が必要
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        if start_date:
            queryset = queryset.filter(
                ordered_at__date__gte=start_date
            )

        if end_date:
            queryset = queryset.filter(
                ordered_at__date__lte=end_date
            )

        # ページネーション
        try:
            page = int(request.query_params.get("page", 1))
            page_size = int(request.query_params.get("page_size", 20))
        except (TypeError, ValueError):
            raise ValidationError({
                "page": ["ページ番号と表示件数は整数で指定してください。"]
            })

        if page < 1 or page_size < 1 or page_size > 100:
            raise ValidationError({
                "page": ["ページ番号は1以上、表示件数は1〜100で指定してください。"]
            })

        total = queryset.count()
        total_pages = (total + page_size - 1) // page_size

        orders = queryset[
            (page - 1) * page_size:page * page_size
        ]

        items = AdminOrderListItemSerializer(
            orders,
            many=True,
        ).data

        response_data = {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

        return Response(
            AdminOrderListResponseSerializer(response_data).data,
            status=status.HTTP_200_OK,
        )


class AdminOrderDetailView(APIView):
    """管理者向け注文詳細"""

    permission_classes = [IsAdminCSOrAdmin]

    def get(self, request, order_id):
        """注文詳細を取得する"""

        order = get_object_or_404(
            Order.objects
            .select_related("user")
            .prefetch_related(
                "order_shipments__order_items",
                "inquiries",
            ),
            pk=order_id,
        )

        # 対象注文に関係する操作履歴を取得
        from marche.models import AuditLog

        operation_history = AuditLog.objects.filter(
            target_type="order",
            target_id=order.id,
        ).select_related("admin").order_by("-created_at")

        serializer = AdminOrderDetailSerializer(
            order,
            context={
                "request": request,
                "operation_history": operation_history,
            },
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


class AdminOrderCancelView(APIView):
    """管理者による注文箱のキャンセル"""

    permission_classes = [IsAdminCSOrAdmin]

    def post(self, request, order_id):
        """指定された箱をキャンセルする"""

        serializer = AdminOrderCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        shipment_ids = serializer.validated_data["shipment_ids"]
        reason = serializer.validated_data["reason"]

        with transaction.atomic():

            order = get_object_or_404(
                Order.objects.select_for_update(),
                pk=order_id,
            )

            shipments = list(
                OrderShipment.objects
                .select_for_update()
                .filter(
                    order=order,
                    id__in=shipment_ids,
                )
            )

            # 指定された箱がすべて対象注文に属しているか確認
            if len(shipments) != len(set(shipment_ids)):
                raise NotFound("指定された配送箱が見つかりません。")

            # すでにキャンセル済みの箱が含まれていないか確認
            if any(shipment.status == "canceled" for shipment in shipments):
                raise APIException(
                    detail="キャンセル済みの配送箱が含まれています。",
                    code="conflict",
                )

            canceled_shipments = []

            for shipment in shipments:

                previous_status = shipment.status

                # 在庫管理対象の商品だけ在庫を戻す
                # 未発送・キャンセル申請中だった箱が対象
                if previous_status in ["unshipped", "cancel_requested"]:

                    order_items = shipment.order_items.select_related(
                        "product"
                    )

                    for item in order_items:

                        product = Product.objects.select_for_update().get(
                            pk=item.product_id
                        )

                        # stock が NULL の商品は在庫管理対象外
                        if product.stock is not None:
                            product.stock += item.quantity
                            product.save(update_fields=["stock"])

                shipment.status = "canceled"
                shipment.cancel_reason = reason
                shipment.canceled_at = timezone.now()
                shipment.save(
                    update_fields=[
                        "status",
                        "cancel_reason",
                        "canceled_at",
                        "updated_at",
                    ]
                )

                canceled_shipments.append({
                    "shipment_id": shipment.id,
                    "previous_status": previous_status,
                })

            # 操作履歴を記録
            record_audit_log(
                admin=request.user,
                action="cancel",
                target_type="order",
                target_id=order.id,
                detail={
                    "shipment_ids": shipment_ids,
                    "reason": reason,
                    "shipments": canceled_shipments,
                },
            )

        return Response(
            {
                "message": "注文のキャンセルを受け付けました。",
                "order_id": order.id,
                "shipment_ids": shipment_ids,
            },
            status=status.HTTP_200_OK,
        )


class AdminOrderRefundView(APIView):
    """管理者による注文の返金"""

    permission_classes = [IsAdminCSOrAdmin]

    def post(self, request, order_id):
        """返金待ちの配送箱を返金済みにする"""

        serializer = AdminOrderRefundSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        shipment_id = serializer.validated_data["shipment_id"]
        method = serializer.validated_data["method"]

        with transaction.atomic():

            order = get_object_or_404(
                Order.objects.select_for_update(),
                pk=order_id,
            )

            shipment = get_object_or_404(
                OrderShipment.objects.select_for_update(),
                pk=shipment_id,
                order=order,
            )

            # 返金待ちの箱だけ返金可能
            if (
                shipment.status != "canceled"
                or shipment.refunded_amount is not None
            ):
                raise APIException(
                    detail="この配送箱は返金対象ではありません。",
                    code="conflict",
                )

            # 箱の返金額を計算
            items_total = shipment.order_items.aggregate(
                total=Sum("subtotal")
            )["total"] or Decimal("0")

            refund_amount = items_total + shipment.shipping_fee

            if refund_amount <= 0:
                raise ValidationError({
                    "shipment_id": ["返金額が不正です。"]
                })

            if method == "stripe":

                # Stripe決済の注文だけStripe返金を許可
                if order.payment_method != "card":
                    raise ValidationError({
                        "method": ["カード決済の注文のみStripe返金できます。"]
                    })

                if not order.stripe_payment_intent_id:
                    raise ValidationError({
                        "method": ["Stripeの決済情報が見つかりません。"]
                    })

                # Stripe APIによる返金処理はサービス層で実装する
                # ※既存のStripe決済サービスとの接続が必要
                raise APIException(
                    detail="Stripe返金サービスとの接続が未実装です。",
                    code="stripe_not_configured",
                )

            elif method == "manual":

                # 銀行振込など、手動返金済みとして記録
                shipment.refunded_amount = refund_amount
                shipment.save(
                    update_fields=[
                        "refunded_amount",
                        "updated_at",
                    ]
                )

            # 操作履歴を記録
            record_audit_log(
                admin=request.user,
                action="refund",
                target_type="order",
                target_id=order.id,
                detail={
                    "shipment_id": shipment.id,
                    "method": method,
                    "refund_amount": str(refund_amount),
                },
            )

        return Response(
            {
                "message": "返金処理が完了しました。",
                "order_id": order.id,
                "shipment_id": shipment.id,
                "method": method,
                "refund_amount": str(refund_amount),
            },
            status=status.HTTP_200_OK,
        )


# """注文・返金管理

# 認証: 管理者（権限グループ: CS・管理者）
# 共通: 管理者APIの共通チェック（is_staff と権限グループ）は common/permissions.py、データ変更はすべて services/audit.py で audit_logs に記録

# このファイルに書くもの（APIView / generics のクラス）。シーケンス図は Notion の同名の図:
#   - 注文一覧（管理者）: GET /api/v1/admin/orders
#       ・注文番号・メールのキーワード、payment_status・箱の status・返金待ちだけ・注文日の範囲
#   - 注文詳細（管理者）: GET /api/v1/admin/orders/:orderId
#       ・購入者の連絡先・決済情報・箱・明細・操作履歴・関係する問い合わせ
#   - 注文キャンセル（管理者）: POST /api/v1/admin/orders/:orderId/cancel
#       ・shipment_ids・reason。発送済みの箱も可。未発送・キャンセル申請中だった箱は在庫を戻す
#       ・カードは自動で部分返金、それ以外は返金待ち。購入者と生産者に通知・メール
#   - 返金: POST /api/v1/admin/orders/:orderId/refund
#       ・返金待ちの箱（canceled かつ refunded_amount が空）に使う
#       ・method: stripe（カードのみ Stripe で再返金）／manual（銀行振込などで返金したことを記録）。返金は箱の全額のみ

# 仕様: claude/api-spec.md / カラム名: claude/er-diagram.md
# """
