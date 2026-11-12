"""注文・配送・キャンセル承認（生産者） のシリアライザー

使う view: api/views/dashboard/orders.py
形は Notion の「注文一覧取得API」「注文詳細取得API」「配送状況更新API」（GET・PATCH /api/v1/dashboard/orders...）に合わせる。
Notion から変えたもの（api-spec「7. 実装で決めたこと」）:
  - etag・If-Match は使わない（同時更新は行ロック＋状態の確認で 409 にする）
  - 一覧の paymentStatus の絞り込みはない（生産者には paid の注文だけを見せる）
  - 配送状況更新の trackingNo は shipped でも任意

レスポンスに入れないもの: 他の生産者の箱・明細、注文全体の金額、購入者のアカウントID・メール、Stripe の ID、閲覧トークン
"""
from rest_framework import serializers

from marche.models import OrderItem, OrderShipment

from ...common.pagination import PageQuerySerializer
from ...common.serializers import StrictSerializer

# BIGINT の上限。これより大きい ID は DB に渡さない
MAX_ID = 2 ** 63 - 1


# =========================================================
# リクエスト
# =========================================================

class DashboardOrderListQuerySerializer(PageQuerySerializer):
    """GET /dashboard/orders の ?shipmentStatus=&page=&pageSize=

    shipmentStatus: 自分の箱に1つでも一致する注文が対象（返す箱は自分の全部の箱）。省略時はすべて
    """

    shipment_status = serializers.ChoiceField(choices=OrderShipment.Status.choices, required=False)


class ShipmentUpdateSerializer(StrictSerializer):
    """PATCH /dashboard/orders/:orderId/shipping の本文 {shipmentId, status, trackingNo}

    status: shipped（unshipped から）/ delivered（shipped から）
    trackingNo: shipped のときだけ任意で送れる（delivered で送ったら 400）
    """

    shipment_id = serializers.IntegerField(min_value=1, max_value=MAX_ID)
    status = serializers.ChoiceField(choices=[OrderShipment.Status.SHIPPED, OrderShipment.Status.DELIVERED])
    tracking_no = serializers.CharField(required=False, allow_null=True, min_length=1, max_length=30)

    def validate(self, attrs):
        if attrs["status"] == OrderShipment.Status.DELIVERED and "tracking_no" in attrs:
            raise serializers.ValidationError({"tracking_no": ["配達完了のときは送り状番号を指定できません。"]})
        return attrs


# =========================================================
# レスポンス
# =========================================================

class OrderItemSerializer(serializers.ModelSerializer):
    """明細（注文時点の値）"""

    class Meta:
        model = OrderItem
        fields = ["id", "product_id", "product_name", "unit_price", "discount_rate", "paid_unit_price", "quantity",
                  "tax_rate", "subtotal"]


class ShipmentSerializer(serializers.ModelSerializer):
    """箱（生産者×温度帯）。明細は prefetch した order_items を使う"""

    items = OrderItemSerializer(source="order_items", many=True)

    class Meta:
        model = OrderShipment
        fields = ["id", "temperature_zone", "status", "shipping_fee", "desired_date", "desired_time", "tracking_no",
                  "shipped_at", "cancel_reason", "canceled_at", "refunded_amount", "updated_at", "items"]


class DashboardOrderSummarySerializer(serializers.Serializer):
    """注文一覧の1件。view で自分の箱だけを my_shipments に prefetch した Order を渡す

    producerItemsTotal: 自分の明細の subtotal の合計 / producerShippingTotal: 自分の箱の送料の合計
    キャンセル・返金があっても注文時の金額のまま（返金済みかは箱の refundedAmount で見る）
    """

    order_id = serializers.IntegerField(source="id")
    order_no = serializers.CharField()
    ordered_at = serializers.DateTimeField()
    payment_status = serializers.CharField()
    producer_items_total = serializers.SerializerMethodField()
    producer_shipping_total = serializers.SerializerMethodField()
    producer_total = serializers.SerializerMethodField()
    shipments = ShipmentSerializer(source="my_shipments", many=True)

    def get_producer_items_total(self, order):
        return sum(item.subtotal for shipment in order.my_shipments for item in shipment.order_items.all())

    def get_producer_shipping_total(self, order):
        return sum(shipment.shipping_fee for shipment in order.my_shipments)

    def get_producer_total(self, order):
        return self.get_producer_items_total(order) + self.get_producer_shipping_total(order)


class ShippingAddressSerializer(serializers.Serializer):
    """注文時点のお届け先（orders.ship_*）"""

    name = serializers.CharField(source="ship_name")
    postal_code = serializers.CharField(source="ship_postal_code")
    prefecture = serializers.CharField(source="ship_prefecture")
    city = serializers.CharField(source="ship_city")
    address_line1 = serializers.CharField(source="ship_address_line1")
    address_line2 = serializers.CharField(source="ship_address_line2", allow_null=True)
    phone = serializers.CharField(source="ship_phone")


class DashboardOrderDetailSerializer(DashboardOrderSummarySerializer):
    """注文詳細 = 一覧の項目＋お届け先（配送に必要なものだけ。購入者のメール・アカウントは返さない）"""

    shipping_address = ShippingAddressSerializer(source="*")


class ShipmentListResponseSerializer(serializers.Serializer):
    """キャンセルの承認・拒否のレスポンス {shipments: [...]}（処理した箱）"""

    shipments = ShipmentSerializer(many=True)
