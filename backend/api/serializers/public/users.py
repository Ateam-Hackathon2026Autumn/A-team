"""会員登録・自分のアカウントのシリアライザー

使う view: api/views/public/users.py
- 新規登録（POST /api/v1/users）: SignupSerializer
- 本人情報の取得・更新（GET・PATCH /api/v1/users/me）: MeSerializer（レスポンス）・ProfileUpdateSerializer
    ・PATCH は送った項目だけ（空のオブジェクトは400）。姓・名は1〜10文字（新規登録と同じ）
    ・phone・birthDate は変えられるが null（削除）は不可。prefectureId は null で未設定に戻せる
    ・interests は配列でまるごと置き換え（空の配列で全部消す）
- メールアドレスの変更（PUT /api/v1/users/me/email）: EmailChangeSerializer {email, currentPassword}
- パスワード変更（PUT /api/v1/users/me/password）: PasswordChangeSerializer {currentPassword, newPassword}
- 退会（DELETE /api/v1/users/me）: WithdrawSerializer {currentPassword}
- 今のパスワードが違うときは 400（details.currentPassword）
"""
import re
from datetime import date

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import serializers

from marche.models import Prefecture, User

from ...common.serializers import StrictSerializer
from .auth import AuthUserSerializer

INTEREST_CHOICES = ["vegetables", "fruits", "seafood", "experiences", "short_term_jobs", "farming"]
PHONE_PATTERN = re.compile(r"^0\d{9,10}$")  # 0から始まる10〜11桁（固定電話・携帯電話）
BIRTH_DATE_MIN = date(1900, 1, 1)


def validate_phone_value(value):
    """半角数字とハイフンだけ受け付け、保存はハイフンを除いた数字だけにする"""
    if not re.fullmatch(r"[0-9-]+", value):
        raise serializers.ValidationError("電話番号は半角数字とハイフンで入力してください。")
    digits = value.replace("-", "")
    if not PHONE_PATTERN.match(digits):
        raise serializers.ValidationError("電話番号の形式が正しくありません。")
    return digits


def validate_birth_date_value(value):
    if value > timezone.localdate():
        raise serializers.ValidationError("生年月日に未来の日付は指定できません。")
    if value < BIRTH_DATE_MIN:
        raise serializers.ValidationError("生年月日を確認してください。")
    return value


def validate_interests_value(value):
    if len(set(value)) != len(value):
        raise serializers.ValidationError("同じ項目が重複しています。")
    return value


def check_current_password(user, password):
    if not user.check_password(password):
        raise serializers.ValidationError({"current_password": ["現在のパスワードが正しくありません。"]})


def check_password_policy(password, user):
    """パスワード規則（settings.AUTH_PASSWORD_VALIDATORS）。氏名・メールに似ていないかも確かめる"""
    try:
        validate_password(password, user=user)
    except DjangoValidationError as e:
        raise serializers.ValidationError({"new_password" if user.pk else "password": list(e.messages)})


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
        return validate_phone_value(value)

    def validate_birth_date(self, value):
        return validate_birth_date_value(value)

    def validate_interests(self, value):
        return validate_interests_value(value)

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
        check_password_policy(attrs["password"], candidate)
        return attrs


# =========================================================
# 本人情報（マイページ）
# =========================================================

class MeProfileSerializer(serializers.Serializer):
    phone = serializers.CharField(allow_null=True)
    birth_date = serializers.DateField(allow_null=True)
    prefecture_id = serializers.IntegerField(allow_null=True)
    interests = serializers.ListField(child=serializers.CharField())


class MeSerializer(serializers.Serializer):
    """GET・PATCH /users/me のレスポンス {user, profile}"""

    user = AuthUserSerializer(source="*")
    profile = MeProfileSerializer(source="*")


class ProfileUpdateSerializer(StrictSerializer):
    """PATCH /users/me。送った項目だけ変える"""

    last_name = serializers.CharField(max_length=10, required=False)
    first_name = serializers.CharField(max_length=10, required=False)
    phone = serializers.CharField(max_length=50, required=False)
    birth_date = serializers.DateField(required=False)
    prefecture_id = serializers.PrimaryKeyRelatedField(
        queryset=Prefecture.objects.all(), source="prefecture", required=False, allow_null=True)
    interests = serializers.ListField(child=serializers.ChoiceField(choices=INTEREST_CHOICES), max_length=6,
                                      required=False)

    def validate_phone(self, value):
        return validate_phone_value(value)

    def validate_birth_date(self, value):
        return validate_birth_date_value(value)

    def validate_interests(self, value):
        return validate_interests_value(value)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError({"non_field_errors": ["変更する項目を指定してください。"]})
        return attrs


class EmailChangeSerializer(StrictSerializer):
    """PUT /users/me/email。context["user"] に本人を渡す"""

    email = serializers.EmailField(max_length=254)
    current_password = serializers.CharField(max_length=128, trim_whitespace=False, write_only=True)

    def validate_email(self, value):
        email = User.objects.normalize_email(value)
        if email == self.context["user"].email:
            raise serializers.ValidationError("今のメールアドレスと同じです。")
        return email

    def validate(self, attrs):
        check_current_password(self.context["user"], attrs["current_password"])
        return attrs


class PasswordChangeSerializer(StrictSerializer):
    """PUT /users/me/password。context["user"] に本人を渡す"""

    current_password = serializers.CharField(max_length=128, trim_whitespace=False, write_only=True)
    new_password = serializers.CharField(max_length=128, trim_whitespace=False, write_only=True)

    def validate(self, attrs):
        user = self.context["user"]
        check_current_password(user, attrs["current_password"])
        if attrs["new_password"] == attrs["current_password"]:
            raise serializers.ValidationError({"new_password": ["今のパスワードと同じパスワードは使えません。"]})
        check_password_policy(attrs["new_password"], user)
        return attrs


class WithdrawSerializer(StrictSerializer):
    """DELETE /users/me。context["user"] に本人を渡す"""

    current_password = serializers.CharField(max_length=128, trim_whitespace=False, write_only=True)

    def validate(self, attrs):
        check_current_password(self.context["user"], attrs["current_password"])
        return attrs
