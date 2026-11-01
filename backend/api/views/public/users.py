"""会員登録・自分のアカウント

- POST /api/v1/users  新規登録（Notion「共通ユーザー新規登録API」）
- プロフィール取得・更新・退会・パスワード変更はステップ7で追加する
"""
from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from marche.models import NotificationSetting, User, UserConsent

from ...common.exceptions import Conflict
from ...common.throttles import IPRateThrottle
from ...serializers.public.users import SignupSerializer
from ...services import email_verification, mail
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
