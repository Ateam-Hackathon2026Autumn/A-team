"""会員登録・自分のアカウントのシリアライザー

使う view: api/views/public/users.py
- 新規登録（POST /api/v1/users）: SignupSerializer
- プロフィール取得・更新・退会・パスワード変更はステップ7で追加する
"""
import re
from datetime import date

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import serializers

from marche.models import Prefecture, User

from ...common.serializers import StrictSerializer

INTEREST_CHOICES = ["vegetables", "fruits", "seafood", "experiences", "short_term_jobs", "farming"]
PHONE_PATTERN = re.compile(r"^0\d{9,10}$")  # 0から始まる10〜11桁（固定電話・携帯電話）
BIRTH_DATE_MIN = date(1900, 1, 1)


class SignupSerializer(StrictSerializer):
    """POST /api/v1/users 新規登録の入力

    Notion「共通ユーザー新規登録API」の requestBody に合わせる。
    メールアドレスの重複・規約の版の不一致は 409 なので、ここではなく view で確認する。
    """

    last_name = serializers.CharField(max_length=10)
    first_name = serializers.CharField(max_length=10)
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(max_length=128, trim_whitespace=False, write_only=True)
    phone = serializers.CharField(max_length=50)
    birth_date = serializers.DateField()
    prefecture_id = serializers.PrimaryKeyRelatedField(
        queryset=Prefecture.objects.all(), source="prefecture", required=False, allow_null=True, default=None
    )
    interests = serializers.ListField(
        child=serializers.ChoiceField(choices=INTEREST_CHOICES), max_length=6, required=False, default=list
    )
    agreed_to_terms = serializers.BooleanField()
    agreed_to_privacy_policy = serializers.BooleanField()
    terms_version = serializers.CharField(max_length=30)
    privacy_policy_version = serializers.CharField(max_length=30)

    def validate_email(self, value):
        return User.objects.normalize_email(value)

    def validate_phone(self, value):
        # 半角数字とハイフンだけ受け付け、保存はハイフンを除いた数字だけにする
        if not re.fullmatch(r"[0-9-]+", value):
            raise serializers.ValidationError("電話番号は半角数字とハイフンで入力してください。")
        digits = value.replace("-", "")
        if not PHONE_PATTERN.match(digits):
            raise serializers.ValidationError("電話番号の形式が正しくありません。")
        return digits

    def validate_birth_date(self, value):
        if value > timezone.localdate():
            raise serializers.ValidationError("生年月日に未来の日付は指定できません。")
        if value < BIRTH_DATE_MIN:
            raise serializers.ValidationError("生年月日を確認してください。")
        return value

    def validate_interests(self, value):
        if len(set(value)) != len(value):
            raise serializers.ValidationError("同じ項目が重複しています。")
        return value

    def validate_agreed_to_terms(self, value):
        if value is not True:
            raise serializers.ValidationError("利用規約への同意が必要です。")
        return value

    def validate_agreed_to_privacy_policy(self, value):
        if value is not True:
            raise serializers.ValidationError("プライバシーポリシーへの同意が必要です。")
        return value

    def validate(self, attrs):
        # パスワード規則（settings.AUTH_PASSWORD_VALIDATORS）。氏名・メールに似ているかの確認のため、仮のユーザーを渡す
        candidate = User(email=attrs["email"], last_name=attrs["last_name"], first_name=attrs["first_name"])
        try:
            validate_password(attrs["password"], user=candidate)
        except DjangoValidationError as e:
            raise serializers.ValidationError({"password": list(e.messages)})
        return attrs
