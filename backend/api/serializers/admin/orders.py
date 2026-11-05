"""管理者向け注文管理APIのシリアライザー

対象API:
    GET  /api/v1/admin/orders
    GET  /api/v1/admin/orders/:orderId
    POST /api/v1/admin/orders/:orderId/cancel
    POST /api/v1/admin/orders/:orderId/refund

注文一覧・詳細・キャンセル・返金処理で使用する。

注意:
    - 既存のDBモデル・テーブル定義は変更しない。
    - フロント側のcamelCaseは共通設定でsnake_caseに変換する。
    - 注文のキャンセル・返金などの業務処理はView側で実装する。
"""

from rest_framework import serializers

from api.common.serializers import StrictSerializer



# 注文キャンセル
# POST /api/v1/admin/orders/:orderId/cancel
class AdminOrderCancelSerializer(StrictSerializer):
    """管理者による注文キャンセルのリクエストを検証する。

    リクエスト:
        {
            "shipmentIds": [2012, 2013],
            "reason": "購入者からキャンセル依頼があったため"
        }
    """

    shipment_ids = serializers.ListField(
        child=serializers.IntegerField(
            min_value=1,
            error_messages={
                "invalid": "配送箱IDは整数で指定してください。",
                "min_value": "配送箱IDは1以上で指定してください。",
            },
        ),
        allow_empty=False,
        error_messages={
            "required": "キャンセル対象の配送箱IDを指定してください。",
            "not_a_list": "配送箱IDはリストで指定してください。",
            "empty": "キャンセル対象の配送箱を1件以上指定してください。",
        },
    )

    reason = serializers.CharField(
        max_length=500,
        allow_blank=False,
        trim_whitespace=True,
        error_messages={
            "required": "キャンセル理由を入力してください。",
            "blank": "キャンセル理由を入力してください。",
            "max_length": "キャンセル理由は500文字以内で入力してください。",
        },
    )

    def validate_shipment_ids(self, value):
        """配送箱IDの重複を確認する。"""

        if len(value) != len(set(value)):
            raise serializers.ValidationError(
                "同じ配送箱IDを複数指定することはできません。"
            )

        return value


# 返金処理
# POST /api/v1/admin/orders/:orderId/refund
class AdminOrderRefundSerializer(StrictSerializer):
    """管理者による返金処理のリクエストを検証する。

    リクエスト:
        {
            "shipmentId": 2012,
            "method": "stripe"
        }

    method:
        stripe: Stripeによる返金
        manual: 手動による返金記録
    """

    shipment_id = serializers.IntegerField(
        min_value=1,
        error_messages={
            "required": "返金対象の配送箱IDを指定してください。",
            "invalid": "配送箱IDは整数で指定してください。",
            "min_value": "配送箱IDは1以上で指定してください。",
        },
    )

    method = serializers.ChoiceField(
        choices=[
            ("stripe", "Stripeによる返金"),
            ("manual", "手動による返金"),
        ],
        error_messages={
            "required": "返金方法を指定してください。",
            "invalid_choice": (
                "返金方法はstripeまたはmanualを指定してください。"
            ),
        },
    )



# 商品明細
class AdminOrderItemSerializer(serializers.Serializer):
    """管理者向け注文の商品明細"""

    id = serializers.IntegerField()

    product_id = serializers.IntegerField()

    product_name = serializers.CharField()

    unit_price = serializers.IntegerField()

    discount_rate = serializers.IntegerField(
        allow_null=True,
    )

    paid_unit_price = serializers.IntegerField()

    quantity = serializers.IntegerField()

    tax_rate = serializers.IntegerField()

    subtotal = serializers.IntegerField()



# 配送箱
class AdminOrderShipmentSerializer(serializers.Serializer):
    """管理者向け注文の配送箱情報"""

    id = serializers.IntegerField()

    producer_id = serializers.IntegerField()

    temperature_zone = serializers.CharField()

    status = serializers.CharField()

    shipping_fee = serializers.IntegerField()

    desired_date = serializers.DateField(
        allow_null=True,
    )

    desired_time = serializers.CharField(
        allow_null=True,
    )

    tracking_no = serializers.CharField(
        allow_null=True,
    )

    shipped_at = serializers.DateTimeField(
        allow_null=True,
    )

    cancel_reason = serializers.CharField(
        allow_null=True,
    )

    canceled_at = serializers.DateTimeField(
        allow_null=True,
    )

    refunded_amount = serializers.IntegerField(
        allow_null=True,
    )

    stripe_refund_id = serializers.CharField(
        allow_null=True,
    )

    items = AdminOrderItemSerializer(
        source="order_items",
        many=True,
    )



# 関連問い合わせ
class AdminOrderInquirySerializer(serializers.Serializer):
    """注文に関連する問い合わせ情報"""

    id = serializers.IntegerField()

    email = serializers.EmailField()

    category = serializers.CharField()

    subject = serializers.CharField()

    status = serializers.CharField()

    priority = serializers.CharField()



# 操作履歴
class AdminOrderAuditLogSerializer(serializers.Serializer):
    """管理者による注文関連の操作履歴"""

    id = serializers.IntegerField()

    admin_id = serializers.IntegerField()

    action = serializers.CharField()

    target_type = serializers.CharField()

    target_id = serializers.IntegerField()

    detail = serializers.JSONField(
        allow_null=True,
    )

    created_at = serializers.DateTimeField()


# 注文一覧
# GET /api/v1/admin/orders
class AdminOrderListItemSerializer(serializers.Serializer):
    """管理者向け注文一覧の1件分のレスポンス"""

    order_id = serializers.IntegerField(
        source="id",
    )

    order_no = serializers.CharField()

    ordered_at = serializers.DateTimeField()

    payment_method = serializers.CharField()

    payment_status = serializers.CharField()

    items_total = serializers.IntegerField()

    shipping_total = serializers.IntegerField()

    grand_total = serializers.IntegerField()

    guest_name = serializers.CharField(
        allow_null=True,
    )

    guest_email = serializers.EmailField(
        allow_null=True,
    )

    guest_phone = serializers.CharField(
        allow_null=True,
    )

    shipments = AdminOrderShipmentSerializer(
        source="order_shipments",
        many=True,
    )


class AdminOrderListResponseSerializer(serializers.Serializer):
    """管理者向け注文一覧のレスポンス"""

    items = AdminOrderListItemSerializer(
        many=True,
    )

    total = serializers.IntegerField()

    page = serializers.IntegerField()

    page_size = serializers.IntegerField()

    total_pages = serializers.IntegerField()


# 注文詳細
# GET /api/v1/admin/orders/:orderId
class AdminOrderDetailSerializer(serializers.Serializer):
    """管理者向け注文詳細のレスポンス"""

    order_id = serializers.IntegerField(
        source="id",
    )

    order_no = serializers.CharField()

    ordered_at = serializers.DateTimeField()

    payment_method = serializers.CharField()

    payment_status = serializers.CharField()

    stripe_payment_intent_id = serializers.CharField(
        allow_null=True,
    )

    items_total = serializers.IntegerField()

    shipping_total = serializers.IntegerField()

    grand_total = serializers.IntegerField()

    tax_8_amount = serializers.IntegerField()

    tax_10_amount = serializers.IntegerField()

    guest_name = serializers.CharField(
        allow_null=True,
    )

    guest_email = serializers.EmailField(
        allow_null=True,
    )

    guest_phone = serializers.CharField(
        allow_null=True,
    )

    ship_name = serializers.CharField()

    ship_postal_code = serializers.CharField()

    ship_prefecture = serializers.CharField()

    ship_city = serializers.CharField()

    ship_address_line1 = serializers.CharField()

    ship_address_line2 = serializers.CharField(
        allow_blank=True,
    )

    ship_phone = serializers.CharField()

    shipments = AdminOrderShipmentSerializer(
        source="order_shipments",
        many=True,
    )

    inquiries = AdminOrderInquirySerializer(
        many=True,
        read_only=True,
    )

    operation_history = serializers.SerializerMethodField()

    def get_operation_history(self, obj):
        """Viewから渡された注文の操作履歴を取得する。

        AuditLogにはOrderとの直接のForeignKeyがないため、
        View側でtarget_typeとtarget_idを使って取得し、
        serializer contextに渡す。
        """

        operation_history = self.context.get(
            "operation_history",
            [],
        )

        return AdminOrderAuditLogSerializer(
            operation_history,
            many=True,
        ).data