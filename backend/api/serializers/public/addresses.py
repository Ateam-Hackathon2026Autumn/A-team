"""お届け先 のシリアライザー

使う view: api/views/public/addresses.py

実装済み:
  - AddressSerializer: レスポンスの1件
      {id, recipientName, postalCode, prefectureId, prefectureName, city, addressLine1, addressLine2, phone,
       isDefault, createdAt, updatedAt}
  - AddressCreateSerializer: 登録（POST）の本文。isDefault は省略可（初期値 false。1件目は view が true にする）
  - AddressUpdateSerializer: 更新（PATCH）の本文。送った項目だけ（空のオブジェクトは400）

受取人名は ER図どおり1つの欄（recipientName、1〜100文字）。郵便番号は 123-4567 の形、電話はハイフンを除いた数字
10〜11桁で保存する（注文のお届け先と同じルール）。都道府県は prefectureId（マスタにないものは400）。
入力エラーは 400（項目ごとのメッセージ）。カラム名は claude/er-diagram.md に合わせる
"""
from rest_framework import serializers

from marche.models import Address, Prefecture

from ...common.serializers import StrictSerializer
from .orders import POSTAL_CODE_PATTERN, normalize_phone


class AddressSerializer(serializers.ModelSerializer):
    """1件。prefecture を select_related しておく"""

    prefecture_name = serializers.CharField(source="prefecture.name")

    class Meta:
        model = Address
        fields = ["id", "recipient_name", "postal_code", "prefecture_id", "prefecture_name", "city",
                  "address_line1", "address_line2", "phone", "is_default", "created_at", "updated_at"]


class AddressCreateSerializer(StrictSerializer):
    recipient_name = serializers.CharField(max_length=100)
    postal_code = serializers.CharField(max_length=8)
    prefecture_id = serializers.PrimaryKeyRelatedField(queryset=Prefecture.objects.all(), source="prefecture")
    city = serializers.CharField(max_length=50)
    address_line1 = serializers.CharField(max_length=100)
    address_line2 = serializers.CharField(max_length=100, required=False, allow_null=True, allow_blank=True)
    phone = serializers.CharField(max_length=20)
    is_default = serializers.BooleanField(required=False, default=False)

    def validate_postal_code(self, value):
        match = POSTAL_CODE_PATTERN.match(value)
        if not match:
            raise serializers.ValidationError("郵便番号は 123-4567 の形で入力してください。")
        return f"{match.group(1)}-{match.group(2)}"

    def validate_phone(self, value):
        return normalize_phone(value)

    def validate_address_line2(self, value):
        return value or None


class AddressUpdateSerializer(AddressCreateSerializer):
    """送った項目だけ変える"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = False
        self.fields["is_default"].default = serializers.empty

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError({"non_field_errors": ["変更する項目を指定してください。"]})
        return attrs
