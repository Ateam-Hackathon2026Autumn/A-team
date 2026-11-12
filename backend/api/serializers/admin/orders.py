"""注文・返金管理（管理者） のシリアライザー

使う view: api/views/admin/orders.py
Notion には名前だけで定義（OpenAPI）がないので、形は api-spec.md と「7. 実装で決めたこと」で決めた。

- 購入者は buyer: {type: member|guest, userId, name, email}（詳細だけ phone も）にまとめる。
  会員は users から、ゲストは orders.guest_* から取る
- 金額はすべて数値（円）
"""
from rest_framework import serializers

from marche.models import AuditLog, Inquiry, Order, OrderItem, OrderShipment

from ...common.pagination import PageQuerySerializer
from ...common.serializers import StrictSerializer

# BIGINT の上限。これより大きい ID は DB に渡さない
MAX_ID = 2 ** 63 - 1


# =========================================================
# リクエスト
# =========================================================

class AdminOrderListQuerySerializer(PageQuerySerializer):
    """GET /admin/orders の ?keyword=&paymentStatus=&shipmentStatus=&refundPending=&startDate=&endDate=&page=&pageSize=

    keyword: 注文番号・メールアドレス（会員・ゲスト）の部分一致
    shipmentStatus: その状態の箱が1つでもある注文 / refundPending=true: 返金待ちの箱がある注文だけ
    startDate・endDate: 注文日（YYYY-MM-DD、日本時間の日付）の範囲。両端を含む
    """

    keyword = serializers.CharField(required=False, max_length=254)
    payment_status = serializers.ChoiceField(choices=Order.PaymentStatus.choices, required=False)
    shipment_status = serializers.ChoiceField(choices=OrderShipment.Status.choices, required=False)
    refund_pending = serializers.BooleanField(required=False)
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)

    def validate(self, attrs):
        start, end = attrs.get("start_date"), attrs.get("end_date")
        if start and end and start > end:
            raise serializers.ValidationError({"end_date": ["終了日は開始日以降の日付を指定してください。"]})
        return attrs


class AdminOrderCancelSerializer(StrictSerializer):
    """POST /admin/orders/:orderId/cancel の本文 {shipmentIds, reason}"""

    shipment_ids = serializers.ListField(
        child=serializers.IntegerField(
            min_value=1, max_value=MAX_ID,
            error_messages={
                "invalid": "配送箱IDは整数で指定してください。",
                "min_value": "配送箱IDは1以上で指定してください。",
            },
        ),
        allow_empty=False,
        max_length=50,
        error_messages={
            "required": "キャンセル対象の配送箱IDを指定してください。",
            "not_a_list": "配送箱IDはリストで指定してください。",
            "empty": "キャンセル対象の配送箱を1件以上指定してください。",
        },
    )
    reason = serializers.CharField(
        max_length=500,
        error_messages={
            "required": "キャンセル理由を入力してください。",
            "blank": "キャンセル理由を入力してください。",
            "max_length": "キャンセル理由は500文字以内で入力してください。",
        },
    )

    def validate_shipment_ids(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError("同じ配送箱IDを複数指定することはできません。")
        return value


class AdminOrderRefundSerializer(StrictSerializer):
    """POST /admin/orders/:orderId/refund の本文 {shipmentId, method}

    method: stripe（カードのみ Stripe で再返金。準備中）／ manual（銀行振込などで返金したことを記録）
    """

    shipment_id = serializers.IntegerField(
        min_value=1, max_value=MAX_ID,
        error_messages={
            "required": "返金対象の配送箱IDを指定してください。",
            "invalid": "配送箱IDは整数で指定してください。",
            "min_value": "配送箱IDは1以上で指定してください。",
        },
    )
    method = serializers.ChoiceField(
        choices=[("stripe", "Stripeによる返金"), ("manual", "手動による返金")],
        error_messages={
            "required": "返金方法を指定してください。",
            "invalid_choice": "返金方法はstripeまたはmanualを指定してください。",
        },
    )


# =========================================================
# レスポンス
# =========================================================

def buyer_of(order, with_phone=False):
    """購入者の連絡先。会員は users、ゲストは orders.guest_*"""
    if order.user_id:
        user = order.user
        buyer = {"type": "member", "user_id": user.id, "name": f"{user.last_name} {user.first_name}",
                 "email": user.email}
        phone = user.phone
    else:
        buyer = {"type": "guest", "user_id": None, "name": order.guest_name, "email": order.guest_email}
        phone = order.guest_phone
    if with_phone:
        buyer["phone"] = phone
    return buyer


class AdminOrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ["id", "product_id", "product_name", "unit_price", "discount_rate", "paid_unit_price", "quantity",
                  "tax_rate", "subtotal"]


class AdminShipmentSerializer(serializers.ModelSerializer):
    """箱。生産者名は producer を select_related、明細は order_items を prefetch しておく"""

    producer_name = serializers.CharField(source="producer.business_name")
    items = AdminOrderItemSerializer(source="order_items", many=True)

    class Meta:
        model = OrderShipment
        fields = ["id", "producer_id", "producer_name", "temperature_zone", "status", "shipping_fee", "desired_date",
                  "desired_time", "tracking_no", "shipped_at", "cancel_reason", "canceled_at", "refunded_amount",
                  "stripe_refund_id", "updated_at", "items"]


class AdminOrderListItemSerializer(serializers.ModelSerializer):
    """注文一覧の1件"""

    order_id = serializers.IntegerField(source="id")
    buyer = serializers.SerializerMethodField()
    shipments = AdminShipmentSerializer(source="order_shipments", many=True)

    class Meta:
        model = Order
        fields = ["order_id", "order_no", "ordered_at", "payment_method", "payment_status", "items_total",
                  "shipping_total", "grand_total", "buyer", "shipments"]

    def get_buyer(self, order):
        return buyer_of(order)


class AdminOrderInquirySerializer(serializers.ModelSerializer):
    class Meta:
        model = Inquiry
        fields = ["id", "email", "category", "subject", "status", "priority", "created_at"]


class AdminAuditLogSerializer(serializers.ModelSerializer):
    admin_name = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = ["id", "admin_id", "admin_name", "action", "detail", "created_at"]

    def get_admin_name(self, log):
        return f"{log.admin.last_name} {log.admin.first_name}"


class AdminOrderDetailSerializer(AdminOrderListItemSerializer):
    """注文詳細 = 一覧の項目＋税額・決済ID・お届け先・関係する問い合わせ・操作履歴（view が operation_history を付ける）"""

    inquiries = AdminOrderInquirySerializer(many=True)
    operation_history = AdminAuditLogSerializer(many=True)

    class Meta(AdminOrderListItemSerializer.Meta):
        fields = AdminOrderListItemSerializer.Meta.fields + [
            "tax_8_amount", "tax_10_amount", "stripe_payment_intent_id",
            "ship_name", "ship_postal_code", "ship_prefecture", "ship_city", "ship_address_line1",
            "ship_address_line2", "ship_phone", "inquiries", "operation_history",
        ]

    def get_buyer(self, order):
        return buyer_of(order, with_phone=True)


class AdminShipmentListResponseSerializer(serializers.Serializer):
    """管理者キャンセルのレスポンス {shipments: [...]}（キャンセルした箱）"""

    shipments = AdminShipmentSerializer(many=True)
