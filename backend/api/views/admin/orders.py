"""注文・返金管理（管理者）

認証: 管理者（権限グループ: CS・管理者。IsAdminCSOrAdmin。未ログイン 401、それ以外は 403）
共通: データを変える操作はすべて services/audit.py で audit_logs に記録する
仕様: api-spec.md「管理者：注文・返金」＋「7. 実装で決めたこと」（Notion には定義なし）。カラム名: claude/er-diagram.md

このファイルの API:
    - 注文一覧: GET /api/v1/admin/orders
        ・keyword（注文番号・メール）・paymentStatus・shipmentStatus・refundPending・startDate・endDate で絞り込み
        ・ordered_at・id の降順。ページングは共通の形。購入者は buyer にまとめる
    - 注文詳細: GET /api/v1/admin/orders/:orderId
        ・購入者の連絡先（phone も）・決済情報・箱・明細・お届け先・関係する問い合わせ・操作履歴
    - 注文キャンセル: POST /api/v1/admin/orders/:orderId/cancel
        ・{shipmentIds, reason}。paid の注文だけ（支払い前の注文は自動キャンセルのバッチに任せる）
        ・発送済みの箱も可。キャンセル済みの箱が含まれていたら 409 SHIPMENT_STATE_CONFLICT
        ・未発送・キャンセル申請中だった箱だけ在庫を戻す
        ・トランザクションが終わってから、カード払いの箱を Stripe で返金して refundedAmount を記録する
          （services/orders.py の refund_canceled_shipments）。コンビニ払い・Stripe のエラーは返金待ちのまま（200）
        ・購入者と、対象の箱の生産者に通知・メール。操作ログ action=cancel
    - 返金: POST /api/v1/admin/orders/:orderId/refund
        ・{shipmentId, method}。返金待ちの箱（canceled かつ refunded_amount が空）だけ。それ以外は 409
        ・manual: 箱の全額（明細の subtotal の合計＋送料）を refunded_amount に記録
        ・stripe: カード払いの箱を Stripe で返金して記録する（services/orders.py の refund_by_stripe）
            コンビニ払い・Stripe のキーがない → 409 STRIPE_REFUND_NOT_AVAILABLE
            Stripe のエラー → 502 STRIPE_ERROR（箱は返金待ちのまま）
        ・どちらも購入者に「返金が完了しました」と通知・メール。操作ログ action=refund。返金した箱を返す
"""
from django.db import transaction
from django.db.models import Exists, OuterRef, Prefetch, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from marche.models import AuditLog, Notification, Order, OrderShipment

from ...common.exceptions import ApiError, Conflict
from ...common.pagination import paginate, validate_query
from ...common.permissions import IsAdminCSOrAdmin
from ...common.serializers import QuerySerializer
from ...serializers.admin.orders import (
    AdminOrderCancelSerializer,
    AdminOrderDetailSerializer,
    AdminOrderListItemSerializer,
    AdminOrderListQuerySerializer,
    AdminOrderRefundSerializer,
    AdminShipmentListResponseSerializer,
    AdminShipmentSerializer,
)
from ...services.audit import record_audit_log
from ...services.notifications import notify, notify_order_buyer
from ...services import payments
from ...services.orders import (
    SHIPMENT_STATE_CONFLICT,
    RefundNotAvailable,
    record_refund,
    refund_by_stripe,
    refund_canceled_shipments,
    restore_stock,
)
from ...services.pricing import refund_amount

Status = OrderShipment.Status
TARGET_TYPE = "order"


def with_shipments(queryset):
    """箱（生産者名つき）と明細をまとめて取る"""
    boxes = OrderShipment.objects.select_related("producer").order_by("id").prefetch_related("order_items")
    return queryset.select_related("user").prefetch_related(Prefetch("order_shipments", queryset=boxes))


class AdminOrderListView(APIView):
    """GET /api/v1/admin/orders"""

    permission_classes = [IsAdminCSOrAdmin]

    def get(self, request):
        query = validate_query(AdminOrderListQuerySerializer, request)
        orders = Order.objects.all()
        if query.get("keyword"):
            keyword = query["keyword"]
            orders = orders.filter(Q(order_no__icontains=keyword) | Q(guest_email__icontains=keyword)
                                   | Q(user__email__icontains=keyword))
        if query.get("payment_status"):
            orders = orders.filter(payment_status=query["payment_status"])
        if query.get("shipment_status"):
            orders = orders.filter(Exists(OrderShipment.objects.filter(
                order=OuterRef("pk"), status=query["shipment_status"])))
        if query.get("refund_pending"):
            orders = orders.filter(Exists(OrderShipment.objects.filter(
                order=OuterRef("pk"), status=Status.CANCELED, refunded_amount__isnull=True)))
        if query.get("start_date"):
            orders = orders.filter(ordered_at__date__gte=query["start_date"])
        if query.get("end_date"):
            orders = orders.filter(ordered_at__date__lte=query["end_date"])

        listed = with_shipments(orders).order_by("-ordered_at", "-id")
        return Response(paginate(listed, query, AdminOrderListItemSerializer, count_queryset=orders))


class AdminOrderDetailView(APIView):
    """GET /api/v1/admin/orders/:orderId"""

    permission_classes = [IsAdminCSOrAdmin]

    def get(self, request, order_id):
        validate_query(QuerySerializer, request)  # クエリパラメーターは受け付けない
        with transaction.atomic():
            order = with_shipments(Order.objects.filter(pk=order_id)).prefetch_related("inquiries").first()
            if order is None:
                raise NotFound()
            order.operation_history = list(
                AuditLog.objects.filter(target_type=TARGET_TYPE, target_id=order.id)
                .select_related("admin").order_by("-created_at", "-id")
            )
            data = AdminOrderDetailSerializer(order).data
        return Response(data)


class AdminOrderCancelView(APIView):
    """POST /api/v1/admin/orders/:orderId/cancel"""

    permission_classes = [IsAdminCSOrAdmin]

    def post(self, request, order_id):
        serializer = AdminOrderCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        shipment_ids = serializer.validated_data["shipment_ids"]
        reason = serializer.validated_data["reason"]

        with transaction.atomic():
            order = Order.objects.select_for_update().select_related("user").filter(pk=order_id).first()
            if order is None:
                raise NotFound()
            shipments = list(
                OrderShipment.objects.select_for_update().filter(order=order, id__in=shipment_ids)
                .select_related("producer__user").order_by("id").prefetch_related("order_items")
            )
            if len(shipments) != len(shipment_ids):
                raise NotFound("指定された配送箱が見つかりません。")
            if order.payment_status != Order.PaymentStatus.PAID:
                raise Conflict(SHIPMENT_STATE_CONFLICT, "支払いが完了していない注文はキャンセルできません。")
            if any(shipment.status == Status.CANCELED for shipment in shipments):
                raise Conflict(SHIPMENT_STATE_CONFLICT, "キャンセル済みの配送箱が含まれています。")

            now = timezone.now()
            history = []
            for shipment in shipments:
                previous = shipment.status
                if previous in (Status.UNSHIPPED, Status.CANCEL_REQUESTED):
                    restore_stock(shipment)  # 発送済み・配達完了の箱は商品が手元にないので戻さない
                shipment.status = Status.CANCELED
                shipment.cancel_reason = reason
                shipment.canceled_at = now
                shipment.save(update_fields=["status", "cancel_reason", "canceled_at", "updated_at"])
                history.append({"shipment_id": shipment.id, "previous_status": previous})

            record_audit_log(admin=request.user, action="cancel", target_type=TARGET_TYPE, target_id=order.id,
                             detail={"reason": reason, "shipments": history})
            notify_admin_cancel(order, shipments, reason)
        refund_canceled_shipments(shipment_ids)
        refreshed = (OrderShipment.objects.filter(pk__in=shipment_ids).select_related("producer").order_by("id")
                     .prefetch_related("order_items"))
        return Response(AdminShipmentListResponseSerializer({"shipments": refreshed}).data)


class AdminOrderRefundView(APIView):
    """POST /api/v1/admin/orders/:orderId/refund"""

    permission_classes = [IsAdminCSOrAdmin]

    def post(self, request, order_id):
        serializer = AdminOrderRefundSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        shipment_id = serializer.validated_data["shipment_id"]
        method = serializer.validated_data["method"]

        with transaction.atomic():
            order = Order.objects.select_for_update().filter(pk=order_id).first()
            shipment = None
            if order is not None:
                shipment = (OrderShipment.objects.select_for_update().filter(pk=shipment_id, order=order)
                            .prefetch_related("order_items").first())
            if shipment is None:
                raise NotFound()
            if shipment.status != Status.CANCELED or shipment.refunded_amount is not None:
                raise Conflict(SHIPMENT_STATE_CONFLICT, "この配送箱は返金待ちではありません。")
            amount = refund_amount(shipment)
            if method == "manual":
                record_refund(shipment.id, amount)
                record_audit_log(admin=request.user, action="refund", target_type=TARGET_TYPE, target_id=order.id,
                                 detail={"shipment_id": shipment.id, "method": method, "refunded_amount": amount})

        if method == "stripe":
            # Stripe の呼び出し中は DB のロックを持たない（トランザクションの外で呼ぶ）
            try:
                refunded = refund_by_stripe(shipment.id)
            except RefundNotAvailable as exc:
                raise Conflict("STRIPE_REFUND_NOT_AVAILABLE", str(exc))
            except payments.PaymentError:
                raise ApiError(status.HTTP_502_BAD_GATEWAY, "STRIPE_ERROR",
                               "Stripe での返金に失敗しました。時間をおいて再度お試しください。")
            if refunded:
                stripe_refund_id = OrderShipment.objects.values_list("stripe_refund_id", flat=True).get(pk=shipment.id)
                record_audit_log(admin=request.user, action="refund", target_type=TARGET_TYPE, target_id=order.id,
                                 detail={"shipment_id": shipment.id, "method": method, "refunded_amount": amount,
                                         "stripe_refund_id": stripe_refund_id})

        refreshed = (OrderShipment.objects.select_related("producer").prefetch_related("order_items")
                     .get(pk=shipment.id))
        return Response(AdminShipmentSerializer(refreshed).data)


def notify_admin_cancel(order, shipments, reason):
    """購入者に1通、対象の箱の生産者に1人1通"""
    names = "、".join(dict.fromkeys(shipment.producer.business_name for shipment in shipments))
    notify_order_buyer(
        order, Notification.NotificationType.CANCELED,
        title="ご注文がキャンセルされました",
        body=(
            f"ご注文（注文番号 {order.order_no}）のうち、{names}の商品を運営がキャンセルしました。\n"
            f"理由: {reason}\n"
            "返金の手続きが完了しましたら、あらためてお知らせします。\n"
        ),
    )
    producers = {shipment.producer_id: shipment.producer for shipment in shipments}
    for producer in producers.values():
        notify(
            producer.user, Notification.NotificationType.CANCELED,
            title="運営が注文をキャンセルしました",
            body=(
                f"注文番号 {order.order_no} のあなたの商品を、運営がキャンセルしました。\n"
                f"理由: {reason}\n"
                "未発送の商品は発送しないでください。\n"
            ),
        )
