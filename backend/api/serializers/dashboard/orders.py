"""注文・配送・キャンセル承認（生産者）のシリアライザー

使う view: api/views/dashboard/orders.py

対象API:
  - GET   /api/v1/dashboard/orders
  - GET   /api/v1/dashboard/orders/:orderId
  - PATCH /api/v1/dashboard/orders/:orderId/shipping
  - POST  /api/v1/dashboard/orders/:orderId/cancel/approve
  - POST  /api/v1/dashboard/orders/:orderId/cancel/reject

入力エラーは400（項目ごとのメッセージ）。
生産者は自分の配送箱と明細だけ取得できる。
"""


from rest_framework import serializers

from api.common.serializers import StrictSerializer, QuerySerializer


# 注文一覧・注文詳細：リクエスト
class DashboardOrderListQuerySerializer(QuerySerializer):
    """注文一覧のクエリパラメータを検証する"""

    page = serializers.IntegerField(
        required=False,
        min_value=1,
        default=1,
        error_messages={
            "invalid": "ページ番号は整数で指定してください。",
            "min_value": "ページ番号は1以上で指定してください。",
        },
    )

    page_size = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=100,
        default=20,
        error_messages={
            "invalid": "表示件数は整数で指定してください。",
            "min_value": "表示件数は1以上で指定してください。",
            "max_value": "表示件数は100以下で指定してください。",
        },
    )


# 注文・配送：レスポンス
class DashboardOrderItemSerializer(serializers.ModelSerializer):
    """注文商品のレスポンス"""

    class Meta:
        from marche.models import OrderItem

        model = OrderItem

        fields = [
            "id",
            "product_id",
            "product_name",
            "unit_price",
            "discount_rate",
            "paid_unit_price",
            "quantity",
            "tax_rate",
            "subtotal",
        ]

        read_only_fields = fields


class DashboardOrderShipmentSerializer(serializers.ModelSerializer):
    """配送箱のレスポンス"""

    items = DashboardOrderItemSerializer(
        source="order_items",
        many=True,
        read_only=True,
    )

    etag = serializers.SerializerMethodField()

    class Meta:
        from marche.models import OrderShipment

        model = OrderShipment

        fields = [
            "id",
            "temperature_zone",
            "status",
            "shipping_fee",
            "desired_date",
            "desired_time",
            "tracking_no",
            "shipped_at",
            "cancel_reason",
            "canceled_at",
            "refunded_amount",
            "updated_at",
            "etag",
            "items",
        ]

        read_only_fields = fields

    def get_etag(self, obj):
        """Viewから渡されたETagを取得する"""

        etags = self.context.get("shipment_etags", {})

        return etags.get(obj.id)


# 生産者の注文箱を取得する共通処理
class ProducerOrderSerializerMixin:
    """ログイン中の生産者に関係する配送箱だけを取得する"""

    def get_producer_shipments(self, obj):
        producer = self.context.get("producer")

        if producer is None:
            return []

        return obj.order_shipments.filter(
            producer=producer
        ).prefetch_related(
            "order_items"
        )


# 注文一覧：レスポンス
class DashboardOrderListItemSerializer(
    ProducerOrderSerializerMixin,
    serializers.ModelSerializer,
):
    """注文一覧の1件分のレスポンス"""

    order_id = serializers.IntegerField(
        source="id",
        read_only=True,
    )

    producer_items_total = serializers.SerializerMethodField()

    producer_shipping_total = serializers.SerializerMethodField()

    producer_total = serializers.SerializerMethodField()

    shipments = serializers.SerializerMethodField()

    class Meta:
        from marche.models import Order

        model = Order

        fields = [
            "order_id",
            "order_no",
            "ordered_at",
            "payment_status",
            "producer_items_total",
            "producer_shipping_total",
            "producer_total",
            "shipments",
        ]

        read_only_fields = fields

    def get_producer_items_total(self, obj):
        """自分の配送箱に含まれる商品の合計金額"""

        shipments = self.get_producer_shipments(obj)

        total = sum(
            (
                item.subtotal
                for shipment in shipments
                for item in shipment.order_items.all()
            ),
            0,
        )

        return total

    def get_producer_shipping_total(self, obj):
        """自分の配送箱の送料合計"""

        shipments = self.get_producer_shipments(obj)

        return sum(
            (shipment.shipping_fee for shipment in shipments),
            0,
        )

    def get_producer_total(self, obj):
        """生産者分の注文合計金額"""

        return (
            self.get_producer_items_total(obj)
            + self.get_producer_shipping_total(obj)
        )

    def get_shipments(self, obj):
        """自分の配送箱だけ返す"""

        shipments = self.get_producer_shipments(obj)

        return DashboardOrderShipmentSerializer(
            shipments,
            many=True,
            context=self.context,
        ).data


class DashboardOrderListResponseSerializer(serializers.Serializer):
    """注文一覧のページネーションレスポンス"""

    items = DashboardOrderListItemSerializer(
        many=True,
        read_only=True,
    )

    total = serializers.IntegerField(read_only=True)

    page = serializers.IntegerField(read_only=True)

    page_size = serializers.IntegerField(read_only=True)

    total_pages = serializers.IntegerField(read_only=True)


# 注文詳細：お届け先レスポンス
class DashboardOrderShippingAddressSerializer(serializers.Serializer):
    """注文時点のお届け先情報"""

    name = serializers.CharField(
        source="ship_name",
        read_only=True,
    )

    postal_code = serializers.CharField(
        source="ship_postal_code",
        read_only=True,
    )

    prefecture = serializers.CharField(
        source="ship_prefecture",
        read_only=True,
    )

    city = serializers.CharField(
        source="ship_city",
        read_only=True,
    )

    address_line1 = serializers.CharField(
        source="ship_address_line1",
        read_only=True,
    )

    address_line2 = serializers.CharField(
        source="ship_address_line2",
        read_only=True,
        allow_null=True,
    )

    phone = serializers.CharField(
        source="ship_phone",
        read_only=True,
    )


# 注文詳細：レスポンス
class DashboardOrderDetailSerializer(
    DashboardOrderListItemSerializer,
):
    """注文詳細のレスポンス"""

    shipping_address = DashboardOrderShippingAddressSerializer(
        source="*",
        read_only=True,
    )

    class Meta(DashboardOrderListItemSerializer.Meta):
        fields = DashboardOrderListItemSerializer.Meta.fields + [
            "shipping_address",
        ]


# 発送登録：リクエスト
class DashboardOrderShippingSerializer(StrictSerializer):
    """発送登録の入力値を検証する

    PATCH /api/v1/dashboard/orders/:orderId/shipping

    shipment_id: 対象の配送箱ID
    tracking_no: 追跡番号（任意）
    """

    shipment_id = serializers.IntegerField(
        required=True,
        min_value=1,
        error_messages={
            "required": "配送箱IDを指定してください。",
            "invalid": "配送箱IDは整数で指定してください。",
            "min_value": "配送箱IDは1以上で指定してください。",
        },
    )

    tracking_no = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=30,
        error_messages={
            "max_length": "追跡番号は30文字以内で入力してください。",
        },
    )


# 発送登録・キャンセル処理：レスポンス
class DashboardOrderActionResponseSerializer(serializers.Serializer):
    """発送・キャンセル処理のレスポンス"""

    message = serializers.CharField(read_only=True)

    order_id = serializers.IntegerField(read_only=True)

    shipment_id = serializers.IntegerField(read_only=True)

    status = serializers.CharField(read_only=True)


# """注文・配送・キャンセル承認（生産者） のシリアライザー

# 使う view: api/views/dashboard/orders.py

# このファイルに書くもの（リクエストの検証用・レスポンスの形用）:
#   - 注文一覧（生産者）（GET /api/v1/dashboard/orders）: クエリ・入力の検証とレスポンス
#   - 注文詳細（生産者）（GET /api/v1/dashboard/orders/:orderId）: クエリ・入力の検証とレスポンス
#   - 発送登録（PATCH /api/v1/dashboard/orders/:orderId/shipping）: 入力の検証とレスポンス
#   - キャンセル承認（POST /api/v1/dashboard/orders/:orderId/cancel/approve）: 入力の検証とレスポンス
#   - キャンセル拒否（POST /api/v1/dashboard/orders/:orderId/cancel/reject）: 入力の検証とレスポンス

# 入力エラーは 400（項目ごとのメッセージ）。カラム名は claude/er-diagram.md に合わせる
# """
