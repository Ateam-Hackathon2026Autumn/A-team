"""会員登録・自分のアカウント

- POST /api/v1/users  新規登録（Notion「共通ユーザー新規登録API」）
- GET /api/v1/users/me  本人情報の取得（Notion「本人情報取得API」）。{user, profile}
- PATCH /api/v1/users/me  本人情報の更新（Notion「本人情報更新API」）。送った項目だけ。メールアドレスは変えられない
- PUT /api/v1/users/me/email  メールアドレスの変更 {email, currentPassword}
    ・使用中のアドレスは 409 EMAIL_ALREADY_EXISTS。変えたら未確認に戻し、新しいアドレスに確認メール、古いアドレスにお知らせ
    ・200 で本人情報（GET と同じ形）
- PUT /api/v1/users/me/password  パスワード変更 {currentPassword, newPassword}
    ・今の端末はログインしたまま（update_session_auth_hash）、ほかの端末は自動でログアウト。お知らせメール。204
- DELETE /api/v1/users/me  退会 {currentPassword}
    ・運営スタッフは 403。進行中の取引があれば 409 ACTIVE_TRANSACTIONS_EXIST（何が残っているかをメッセージに書く）
    ・本人にメールしてから匿名化（services/anonymize.py）。生産者なら掲載停止。今のセッションを消して 204
- 今のパスワードが違うときは 400（details.currentPassword）。パスワードを確かめるAPI（メール変更・パスワード変更・
  退会）は同じIPから1時間10回まで（回数制限 password_check）
- どれもメール未確認でも使える
"""
from django.conf import settings
from django.contrib.auth import logout, update_session_auth_hash
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from marche.models import NotificationSetting, User, UserConsent

from ...common.exceptions import ApiError, Conflict
from ...common.throttles import IPRateThrottle
from ...serializers.public.users import (
    EmailChangeSerializer,
    MeSerializer,
    PasswordChangeSerializer,
    ProfileUpdateSerializer,
    SignupSerializer,
    WithdrawSerializer,
)
from ...services import email_verification, mail
from ...services.anonymize import active_transactions, anonymize_user
from .auth import already_authenticated, auth_response, login_and_merge_cart


def email_already_exists():
    return Conflict("EMAIL_ALREADY_EXISTS", "このメールアドレスは既に登録されています。")


class SignupView(APIView):
    """POST /api/v1/users 新規登録

    1. 匿名リクエストにも CSRF を確認する（認証クラス）
    2. 入力値を検証する（400）。規約の版が現行と違えば 409 POLICY_VERSION_MISMATCH
    3. メールアドレスの重複は 409 EMAIL_ALREADY_EXISTS（大文字・小文字は区別しない）
    4. ユーザー・同意履歴・通知設定を同じトランザクションで作る
    5. 自動ログインし、ゲストのときのカートを付け替える
    6. コミット後に確認メールを送る（失敗しても登録は成功のまま。再送APIで救う）
    - すでにログイン済みなら 409 ALREADY_AUTHENTICATED
    - 同じIPから1時間10回まで
    """

    permission_classes = [AllowAny]
    throttle_classes = [IPRateThrottle]
    throttle_scope = "signup"

    def post(self, request):
        if request.user.is_authenticated:
            raise already_authenticated()

        s = SignupSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        data = s.validated_data

        if (data["terms_version"] != settings.TERMS_VERSION
                or data["privacy_policy_version"] != settings.PRIVACY_POLICY_VERSION):
            raise Conflict("POLICY_VERSION_MISMATCH", "利用規約またはプライバシーポリシーが更新されています。内容を確認して、もう一度同意してください。")

        if User.objects.filter(email=data["email"]).exists():
            raise email_already_exists()

        now = timezone.now()
        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    email=data["email"],
                    password=data["password"],
                    last_name=data["last_name"],
                    first_name=data["first_name"],
                    phone=data["phone"],
                    birth_date=data["birth_date"],
                    prefecture=data["prefecture"],
                    interests=data["interests"],
                )
                UserConsent.objects.bulk_create([
                    UserConsent(user=user, document_type=UserConsent.DocumentType.TERMS,
                                version=data["terms_version"], agreed_at=now),
                    UserConsent(user=user, document_type=UserConsent.DocumentType.PRIVACY_POLICY,
                                version=data["privacy_policy_version"], agreed_at=now),
                ])
                NotificationSetting.objects.create(user=user)

                token = email_verification.make_token(user)
                transaction.on_commit(lambda: mail.send_email_verification(user, token))
        except IntegrityError:
            # 同じメールアドレスの登録が同時に来た場合（DB の一意制約で検出）
            raise email_already_exists()

        login_and_merge_cart(request, user)
        return auth_response("登録が完了しました。確認メールの配送を受け付けました。", user,
                                status_code=status.HTTP_201_CREATED)


# =========================================================
# 本人情報（マイページ）
# =========================================================

# パスワードを確かめるAPI（メール変更・パスワード変更・退会）の回数制限。同じIPから1時間10回まで
PASSWORD_CHECK_SCOPE = "password_check"


def me_response(user, status_code=status.HTTP_200_OK):
    user = User.objects.select_related("producer").get(pk=user.pk)
    return Response(MeSerializer(user).data, status=status_code)


def full_name(user):
    return f"{user.last_name} {user.first_name}".strip()


class MeView(APIView):
    """GET・PATCH・DELETE /api/v1/users/me"""

    permission_classes = [IsAuthenticated]
    throttle_scope = PASSWORD_CHECK_SCOPE

    def get_throttles(self):
        return [IPRateThrottle()] if self.request.method == "DELETE" else []  # 退会のときだけ数える

    def get(self, request):
        return me_response(request.user)

    def patch(self, request):
        serializer = ProfileUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        for field, value in serializer.validated_data.items():
            setattr(user, field, value)
        user.save()
        return me_response(user)

    def delete(self, request):
        user = request.user
        serializer = WithdrawSerializer(data=request.data, context={"user": user})
        serializer.is_valid(raise_exception=True)
        if user.is_staff:
            raise ApiError(status.HTTP_403_FORBIDDEN, "FORBIDDEN", "運営スタッフのアカウントは退会できません。")
        remaining = active_transactions(user)
        if remaining:
            raise Conflict("ACTIVE_TRANSACTIONS_EXIST",
                           "次の取引が終わるまで退会できません：" + "、".join(remaining))

        email, name = user.email, full_name(user)
        with transaction.atomic():
            user = User.objects.select_for_update().get(pk=user.pk)
            anonymize_user(user)
            transaction.on_commit(lambda: mail.send_account_notice(
                email, name, "退会が完了しました",
                "退会の手続きが完了しました。これまでのご利用ありがとうございました。\n"
                "ご注文・ご予約などの記録は、お問い合わせへの対応のために残しています。"))
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class EmailChangeView(APIView):
    """PUT /api/v1/users/me/email"""

    permission_classes = [IsAuthenticated]
    throttle_classes = [IPRateThrottle]
    throttle_scope = PASSWORD_CHECK_SCOPE

    def put(self, request):
        user = request.user
        serializer = EmailChangeSerializer(data=request.data, context={"user": user})
        serializer.is_valid(raise_exception=True)
        new_email = serializer.validated_data["email"]
        if User.objects.filter(email=new_email).exclude(pk=user.pk).exists():
            raise email_already_exists()

        old_email = user.email
        try:
            with transaction.atomic():
                user.email = new_email
                user.email_verified_at = None
                user.save(update_fields=["email", "email_verified_at", "updated_at"])
                token = email_verification.make_token(user)
                name = full_name(user)
                transaction.on_commit(lambda: mail.send_email_change_verification(user, token))
                transaction.on_commit(lambda: mail.send_account_notice(
                    old_email, name, "メールアドレスが変更されました",
                    f"ログインに使うメールアドレスが {new_email} に変更されました。\n"
                    "このアドレスには、今後お知らせが届かなくなります。"))
        except IntegrityError:
            raise email_already_exists()
        return me_response(user)


class PasswordChangeView(APIView):
    """PUT /api/v1/users/me/password"""

    permission_classes = [IsAuthenticated]
    throttle_classes = [IPRateThrottle]
    throttle_scope = PASSWORD_CHECK_SCOPE

    def put(self, request):
        user = request.user
        serializer = PasswordChangeSerializer(data=request.data, context={"user": user})
        serializer.is_valid(raise_exception=True)
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password", "updated_at"])
        update_session_auth_hash(request, user)  # 今の端末はログインしたまま。ほかの端末はログアウトになる
        email, name = user.email, full_name(user)
        transaction.on_commit(lambda: mail.send_account_notice(
            email, name, "パスワードが変更されました", "ログインに使うパスワードが変更されました。"))
        return Response(status=status.HTTP_204_NO_CONTENT)
