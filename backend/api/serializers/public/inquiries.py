"""問い合わせ のシリアライザー

使う view: api/views/public/inquiries.py

  - 問い合わせ送信（POST /api/v1/inquiries）: InquiryCreateSerializer {category, subject, body, email, orderId}
      ・email はゲストだけ必須。会員は登録のメールアドレスに返信するので送らせない（送ったら 400）
      ・orderId はログイン中の会員の自分の注文だけ（ゲスト・他人の注文は 400）
      → 会員かどうかで変わる確認は context["user"]（ゲストは None）を見て validate で行う
  - レスポンス: InquirySerializer {id, category, subject, createdAt}

入力エラーは 400（項目ごとのメッセージ）。カラム名は claude/er-diagram.md に合わせる
"""
from rest_framework import serializers

from marche.models import Inquiry, Order, User

from ...common.serializers import StrictSerializer

MAX_ID = 2 ** 63 - 1


class InquiryCreateSerializer(StrictSerializer):
    category = serializers.ChoiceField(choices=Inquiry.Category.choices)
    subject = serializers.CharField(max_length=100)
    body = serializers.CharField(max_length=5000)
    email = serializers.EmailField(max_length=254, required=False)
    order_id = serializers.IntegerField(min_value=1, max_value=MAX_ID, required=False, allow_null=True)

    def validate_email(self, value):
        return User.objects.normalize_email(value)

    def validate(self, attrs):
        user = self.context["user"]
        errors = {}
        if user is None:
            if "email" not in attrs:
                errors["email"] = ["返信先のメールアドレスを入力してください。"]
        elif "email" in attrs:
            errors["email"] = ["ログイン中は、登録のメールアドレスにご返信します。"]

        order_id = attrs.get("order_id")
        if order_id is not None:
            if user is None:
                errors["order_id"] = ["注文を指定するにはログインしてください。"]
            else:
                attrs["order"] = Order.objects.filter(pk=order_id, user=user).first()
                if attrs["order"] is None:
                    errors["order_id"] = ["注文が見つかりません。"]
        if errors:
            raise serializers.ValidationError(errors)
        return attrs


class InquirySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    category = serializers.CharField()
    subject = serializers.CharField()
    created_at = serializers.DateTimeField()
