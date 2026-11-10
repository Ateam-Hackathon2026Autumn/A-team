"""注文・注文履歴・キャンセル申請（会員・ゲスト） のシリアライザー

使う view: api/views/public/orders.py

実装済み:
  - OrderCreateSerializer: POST /api/v1/orders の本文 {shippingAddress, paymentMethod, expectedGrandTotal}
  - GuestOrderCreateSerializer: POST /api/v1/guest/orders の本文（上に guestContact を足したもの）
  - レスポンス（201）は view が組み立てる: {id, orderNo, paymentStatus, itemsTotal, shippingTotal, grandTotal,
    checkoutUrl, expiresAt}
  - MyOrderListQuerySerializer / MyOrderSummarySerializer: 注文履歴一覧（GET /api/v1/users/me/orders）
      1件 {id, orderNo, paymentStatus, paymentMethod, itemsTotal, shippingTotal, grandTotal, orderedAt,
           shipments: [{id, producerId, producerName, temperatureZone, status, shippingFee}]}
  - MyOrderDetailSerializer: 注文詳細（会員・ゲスト共通）
      一覧の項目＋tax8Amount・tax10Amount・shippingAddress・shipments（箱ごとに producer {id, businessName}・
      trackingNo・shippedAt・cancelReason・canceledAt・refundedAmount・cancellable・items）。ゲストは buyer（連絡先）も
      cancellable は view が context["cancellable_producer_ids"] で渡す
  - CancelRequestSerializer: キャンセル申請の本文 {producerId, cancelReason（1〜500文字）}

入力エラーは 400（項目ごとのメッセージ）。カラム名は claude/er-diagram.md に合わせる
"""
import re

from rest_framework import serializers

from marche.models import Order, OrderItem, OrderShipment, Prefecture, User

from ...common.pagination import PageQuerySerializer
from ...common.serializers import StrictSerializer
from ..dashboard.orders import ShippingAddressSerializer as OrderShippingAddressSerializer
from .users import PHONE_PATTERN

POSTAL_CODE_PATTERN = re.compile(r"^([0-9]{3})-?([0-9]{4})$")
NAME_MAX = 100  # 姓と名を半角空白でつないだ長さの上限（orders.ship_name・guest_name）
MAX_AMOUNT = 99_999_999  # 合計金額の上限（Stripe の上限）


def normalize_phone(value):
    """半角数字とハイフンだけ受け付け、ハイフンを除いた数字（0から始まる10〜11桁）にする（新規登録と同じルール）"""
    if not re.fullmatch(r"[0-9-]+", value):
        raise serializers.ValidationError("電話番号は半角数字とハイフンで入力してください。")
    digits = value.replace("-", "")
    if not PHONE_PATTERN.match(digits):
        raise serializers.ValidationError("電話番号の形式が正しくありません。")
    return digits


def check_name_length(data):
    if len(data["last_name"]) + 1 + len(data["first_name"]) > NAME_MAX:
        raise serializers.ValidationError({"first_name": [f"姓と名を合わせて{NAME_MAX - 1}文字以内で入力してください。"]})


class ShippingAddressSerializer(StrictSerializer):
    """お届け先。注文時点の値として orders.ship_* に写す"""

    last_name = serializers.CharField(max_length=50)
    first_name = serializers.CharField(max_length=50)
    postal_code = serializers.CharField(max_length=8)
    prefecture = serializers.CharField(max_length=10)
    city = serializers.CharField(max_length=50)
    address_line1 = serializers.CharField(max_length=100)
    address_line2 = serializers.CharField(max_length=100, required=False, allow_null=True, allow_blank=True)
    phone = serializers.CharField(max_length=20)

    def validate_postal_code(self, value):
        match = POSTAL_CODE_PATTERN.match(value)
        if not match:
            raise serializers.ValidationError("郵便番号は 123-4567 の形で入力してください。")
        return f"{match.group(1)}-{match.group(2)}"

    def validate_prefecture(self, value):
        if not Prefecture.objects.filter(name=value).exists():
            raise serializers.ValidationError("都道府県を選んでください。")
        return value

    def validate_phone(self, value):
        return normalize_phone(value)

    def validate(self, data):
        check_name_length(data)
        return data


class GuestContactSerializer(StrictSerializer):
    """ゲストの連絡先。orders.guest_name（姓 名）・guest_email・guest_phone に入れる"""

    last_name = serializers.CharField(max_length=50)
    first_name = serializers.CharField(max_length=50)
    email = serializers.EmailField(max_length=254)
    phone = serializers.CharField(max_length=20)

    def validate_email(self, value):
        return User.objects.normalize_email(value)

    def validate_phone(self, value):
        return normalize_phone(value)

    def validate(self, data):
        check_name_length(data)
        return data


class OrderCreateSerializer(StrictSerializer):
    """POST /api/v1/orders（会員）の本文。expectedGrandTotal は確認画面で見せた合計（違えば 409 QUOTE_CHANGED）"""

    shipping_address = ShippingAddressSerializer()
    payment_method = serializers.ChoiceField(choices=["card", "konbini"])
    expected_grand_total = serializers.IntegerField(min_value=0, max_value=MAX_AMOUNT)


class GuestOrderCreateSerializer(OrderCreateSerializer):
    """POST /api/v1/guest/orders（ゲスト）の本文"""

    guest_contact = GuestContactSerializer()


# =========================================================
# 注文履歴・詳細・キャンセル申請
# =========================================================

MAX_ID = 2 ** 63 - 1
CANCEL_REASON_MAX = 500


class MyOrderListQuerySerializer(PageQuerySerializer):
    payment_status = serializers.ChoiceField(choices=Order.PaymentStatus.choices, required=False)


class MyShipmentSummarySerializer(serializers.ModelSerializer):
    """一覧の箱。producer を select_related しておく"""

    producer_name = serializers.CharField(source="producer.business_name")

    class Meta:
        model = OrderShipment
        fields = ["id", "producer_id", "producer_name", "temperature_zone", "status", "shipping_fee"]


class MyOrderSummarySerializer(serializers.ModelSerializer):
    """注文履歴一覧の1件。箱は order_shipments を prefetch しておく（id 順）"""

    shipments = MyShipmentSummarySerializer(source="order_shipments", many=True)

    class Meta:
        model = Order
        fields = ["id", "order_no", "payment_status", "payment_method", "items_total", "shipping_total",
                  "grand_total", "ordered_at", "shipments"]


class MyOrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ["id", "product_id", "product_name", "unit_price", "discount_rate", "paid_unit_price", "quantity",
                  "tax_rate", "subtotal"]


class MyShipmentProducerSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    business_name = serializers.CharField()


class MyShipmentSerializer(serializers.ModelSerializer):
    """詳細の箱。producer を select_related、order_items を prefetch しておく"""

    producer = MyShipmentProducerSerializer()
    cancellable = serializers.SerializerMethodField()
    items = MyOrderItemSerializer(source="order_items", many=True)

    class Meta:
        model = OrderShipment
        fields = ["id", "producer", "temperature_zone", "status", "shipping_fee", "tracking_no", "shipped_at",
                  "cancel_reason", "canceled_at", "refunded_amount", "cancellable", "items"]

    def get_cancellable(self, shipment):
        return shipment.producer_id in self.context.get("cancellable_producer_ids", ())


class GuestBuyerSerializer(serializers.Serializer):
    name = serializers.CharField(source="guest_name")
    email = serializers.CharField(source="guest_email")
    phone = serializers.CharField(source="guest_phone")


class MyOrderDetailSerializer(MyOrderSummarySerializer):
    """注文詳細（会員）"""

    shipping_address = OrderShippingAddressSerializer(source="*")
    shipments = MyShipmentSerializer(source="order_shipments", many=True)

    class Meta(MyOrderSummarySerializer.Meta):
        fields = ["id", "order_no", "payment_status", "payment_method", "items_total", "shipping_total",
                  "grand_total", "tax_8_amount", "tax_10_amount", "ordered_at", "shipping_address", "shipments"]


class GuestOrderDetailSerializer(MyOrderDetailSerializer):
    """注文詳細（ゲスト）。会員の詳細に購入者の連絡先を足す"""

    buyer = GuestBuyerSerializer(source="*")

    class Meta(MyOrderDetailSerializer.Meta):
        fields = MyOrderDetailSerializer.Meta.fields + ["buyer"]


class CancelRequestSerializer(StrictSerializer):
    """キャンセル申請の本文。その生産者の箱をまとめて申請する"""

    producer_id = serializers.IntegerField(min_value=1, max_value=MAX_ID)
    cancel_reason = serializers.CharField(max_length=CANCEL_REASON_MAX)
