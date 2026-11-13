"""注文・配送・キャンセル承認（生産者）

認証: 承認済みの生産者（IsApprovedProducer。未ログイン 401、生産者でない・承認前は 403）
      掲載停止中でも、注文の閲覧・発送・キャンセルの承認と拒否はできる（api-spec「生産者APIの共通チェック」）
仕様: Notion の各API定義＋api-spec.md「7. 実装で決めたこと」。カラム名: claude/er-diagram.md

このファイルの API:
    - 注文一覧: GET /api/v1/dashboard/orders
        ・自分の箱がある paid の注文だけ。ordered_at・id の降順。shipmentStatus で絞り込み
        ・返す箱は自分の箱だけ（Prefetch で my_shipments に取る）。N+1 にしない
    - 注文詳細: GET /api/v1/dashboard/orders/:orderId
        ・一覧の項目＋お届け先（ship_*）。他の生産者の箱・購入者のメールは返さない。対象外は 404
    - 配送状況更新: PATCH /api/v1/dashboard/orders/:orderId/shipping
        ・{shipmentId, status, trackingNo}。箱1つだけ。自分の箱でなければ 404
        ・unshipped → shipped（shipped_at を入れ、購入者に通知・メール）/ shipped → delivered
        ・注文が paid でない・状態が合わないときは 409 SHIPMENT_STATE_CONFLICT。更新した箱を返す
    - キャンセル承認: POST /api/v1/dashboard/orders/:orderId/cancel/approve
        ・自分の cancel_requested の箱をまとめて canceled にし、在庫を戻す。購入者に通知・メール
        ・トランザクションが終わってから、カード払いの箱を Stripe で返金して refundedAmount を記録する
          （services/orders.py の refund_canceled_shipments）。コンビニ払い・Stripe のエラーは返金待ちのまま（200）
    - キャンセル拒否: POST /api/v1/dashboard/orders/:orderId/cancel/reject
        ・自分の cancel_requested の箱をまとめて unshipped に戻す。購入者に通知・メール（cancel_rejected）
        ・承認・拒否とも、対象の箱がなければ 409 SHIPMENT_STATE_CONFLICT。処理した箱を {shipments} で返す

同時更新: 注文 → 箱の順に行をロック（select_for_update）してから状態を確かめる。ゲストの購入者にはメールだけ送る。
"""
from django.db import transaction
from django.db.models import Exists, OuterRef, Prefetch
from django.utils import timezone
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from marche.models import Notification, Order, OrderShipment

from ...common.exceptions import Conflict
from ...common.pagination import paginate, validate_query
from ...common.permissions import IsApprovedProducer
from ...common.serializers import QuerySerializer, StrictSerializer
from ...serializers.dashboard.orders import (
    DashboardOrderDetailSerializer,
    DashboardOrderListQuerySerializer,
    DashboardOrderSummarySerializer,
    ShipmentListResponseSerializer,
    ShipmentSerializer,
    ShipmentUpdateSerializer,
)
from ...services.notifications import notify_order_buyer
from ...services.orders import SHIPMENT_STATE_CONFLICT, refund_canceled_shipments, restore_stock

Status = OrderShipment.Status


def producer_orders(producer, shipment_status=None):
    """自分の箱がある paid の注文（新しい順）。自分の箱と明細を my_shipments に prefetch する"""
    my_boxes = OrderShipment.objects.filter(order=OuterRef("pk"), producer=producer)
    if shipment_status:
        my_boxes = my_boxes.filter(status=shipment_status)
    return (
        Order.objects
        .filter(Exists(my_boxes), payment_status=Order.PaymentStatus.PAID)
        .prefetch_related(Prefetch(
            "order_shipments",
            queryset=OrderShipment.objects.filter(producer=producer).order_by("id").prefetch_related("order_items"),
            to_attr="my_shipments",
        ))
        .order_by("-ordered_at", "-id")
    )


def lock_my_shipments(order_id, producer):
    """注文と自分の箱をロックして返す。paid の注文で自分の箱がなければ 404"""
    order = Order.objects.select_for_update().filter(pk=order_id, payment_status=Order.PaymentStatus.PAID).first()
    if order is None:
        raise NotFound()
    shipments = list(
        OrderShipment.objects.select_for_update().filter(order=order, producer=producer)
        .order_by("id").prefetch_related("order_items")
    )
    if not shipments:
        raise NotFound()
    return order, shipments


def cancel_requested_only(shipments, action):
    targets = [shipment for shipment in shipments if shipment.status == Status.CANCEL_REQUESTED]
    if not targets:
        raise Conflict(SHIPMENT_STATE_CONFLICT, f"{action}できるキャンセル申請がありません。")
    return targets


class DashboardOrderListView(APIView):
    """GET /api/v1/dashboard/orders"""

    permission_classes = [IsApprovedProducer]

    def get(self, request):
        query = validate_query(DashboardOrderListQuerySerializer, request)
        orders = producer_orders(request.user.producer, query.get("shipment_status"))
        return Response(paginate(orders, query, DashboardOrderSummarySerializer))


class DashboardOrderDetailView(APIView):
    """GET /api/v1/dashboard/orders/:orderId"""

    permission_classes = [IsApprovedProducer]

    def get(self, request, order_id):
        validate_query(QuerySerializer, request)  # クエリパラメーターは受け付けない
        with transaction.atomic():  # 注文・箱・明細を同じ時点で読む
            order = producer_orders(request.user.producer).filter(pk=order_id).first()
            if order is None:
                raise NotFound()
            data = DashboardOrderDetailSerializer(order).data
        return Response(data)


class DashboardOrderShippingView(APIView):
    """PATCH /api/v1/dashboard/orders/:orderId/shipping"""

    permission_classes = [IsApprovedProducer]

    def patch(self, request, order_id):
        serializer = ShipmentUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        producer = request.user.producer

        with transaction.atomic():
            order = Order.objects.select_for_update().filter(pk=order_id).first()
            shipment = None
            if order is not None:
                shipment = OrderShipment.objects.select_for_update().filter(
                    pk=data["shipment_id"], order=order, producer=producer).first()
            if shipment is None:
                raise NotFound()
            if order.payment_status != Order.PaymentStatus.PAID:
                raise Conflict(SHIPMENT_STATE_CONFLICT, "支払いが完了していない注文は発送できません。")

            if data["status"] == Status.SHIPPED:
                if shipment.status != Status.UNSHIPPED:
                    raise Conflict(SHIPMENT_STATE_CONFLICT, "未発送の箱だけ発送済みにできます。")
                shipment.status = Status.SHIPPED
                shipment.tracking_no = data.get("tracking_no")
                shipment.shipped_at = timezone.now()
                shipment.save(update_fields=["status", "tracking_no", "shipped_at", "updated_at"])
                notify_shipped(order, shipment, producer)
            else:
                if shipment.status != Status.SHIPPED:
                    raise Conflict(SHIPMENT_STATE_CONFLICT, "発送済みの箱だけ配達完了にできます。")
                shipment.status = Status.DELIVERED
                shipment.save(update_fields=["status", "updated_at"])
            body = ShipmentSerializer(shipment).data
        return Response(body)


class DashboardOrderCancelApproveView(APIView):
    """POST /api/v1/dashboard/orders/:orderId/cancel/approve"""

    permission_classes = [IsApprovedProducer]

    def post(self, request, order_id):
        validate_body_empty(request)
        producer = request.user.producer
        with transaction.atomic():
            order, shipments = lock_my_shipments(order_id, producer)
            targets = cancel_requested_only(shipments, "承認")
            now = timezone.now()
            for shipment in targets:
                restore_stock(shipment)
                shipment.status = Status.CANCELED
                shipment.canceled_at = now
                shipment.save(update_fields=["status", "canceled_at", "updated_at"])
            notify_order_buyer(
                order, Notification.NotificationType.CANCELED,
                title="キャンセルが確定しました",
                body=(
                    f"ご注文（注文番号 {order.order_no}）のうち、{producer.business_name}の商品のキャンセルが確定しました。\n"
                    "返金の手続きが完了しましたら、あらためてお知らせします。\n"
                ),
            )
        target_ids = [shipment.id for shipment in targets]
        refund_canceled_shipments(target_ids)
        shipments = OrderShipment.objects.filter(pk__in=target_ids).order_by("id").prefetch_related("order_items")
        return Response(ShipmentListResponseSerializer({"shipments": shipments}).data)


class DashboardOrderCancelRejectView(APIView):
    """POST /api/v1/dashboard/orders/:orderId/cancel/reject"""

    permission_classes = [IsApprovedProducer]

    def post(self, request, order_id):
        validate_body_empty(request)
        producer = request.user.producer
        with transaction.atomic():
            order, shipments = lock_my_shipments(order_id, producer)
            targets = cancel_requested_only(shipments, "拒否")
            for shipment in targets:
                shipment.status = Status.UNSHIPPED
                shipment.save(update_fields=["status", "updated_at"])
            notify_order_buyer(
                order, Notification.NotificationType.CANCEL_REJECTED,
                title="キャンセル申請が承認されませんでした",
                body=(
                    f"ご注文（注文番号 {order.order_no}）のうち、{producer.business_name}の商品のキャンセル申請は"
                    "承認されませんでした。商品は通常どおり発送されます。\n"
                    "ご不明な点は、生産者へのメッセージまたはお問い合わせからご連絡ください。\n"
                ),
            )
            body = ShipmentListResponseSerializer({"shipments": targets}).data
        return Response(body)


def validate_body_empty(request):
    """本文を受け付けない API。項目が送られてきたら 400（StrictSerializer）"""
    serializer = StrictSerializer(data=request.data or {})
    serializer.is_valid(raise_exception=True)


def notify_shipped(order, shipment, producer):
    tracking = f"送り状番号: {shipment.tracking_no}\n" if shipment.tracking_no else ""
    notify_order_buyer(
        order, Notification.NotificationType.SHIPPED,
        title="商品を発送しました",
        body=f"ご注文（注文番号 {order.order_no}）の{producer.business_name}の商品を発送しました。\n{tracking}",
    )

