"""注文・注文履歴・キャンセル申請（会員・ゲスト） のシリアライザー

使う view: api/views/public/orders.py

実装済み:
  - OrderCreateSerializer: POST /api/v1/orders の本文 {shippingAddress, paymentMethod, expectedGrandTotal}
  - GuestOrderCreateSerializer: POST /api/v1/guest/orders の本文（上に guestContact を足したもの）
  - レスポンス（201）は view が組み立てる: {id, orderNo, paymentStatus, itemsTotal, shippingTotal, grandTotal,
    checkoutUrl, expiresAt}

これから書くもの（ステップ6b）:
  - 注文履歴一覧（GET /api/v1/users/me/orders）・注文詳細（会員・ゲスト）・キャンセル申請（会員・ゲスト）

入力エラーは 400（項目ごとのメッセージ）。カラム名は claude/er-diagram.md に合わせる
"""
import re

from rest_framework import serializers

from marche.models import Prefecture, User

from ...common.serializers import StrictSerializer
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
