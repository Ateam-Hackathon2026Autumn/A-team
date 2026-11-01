"""認証（CSRF取得・ログイン・ログインチェック・ログアウト・メール認証）

Notion の API 定義（認証・ユーザー）に合わせる。新規登録（POST /api/v1/users）は users.py。
- GET  /api/v1/auth/csrf                         CSRFトークン取得
- POST /api/v1/auth/signin                       ログイン
- GET  /api/v1/auth/session                      ログインチェック
- POST /api/v1/auth/signout                      ログアウト
- POST /api/v1/auth/email-verification/resend    確認メール再送
- POST /api/v1/auth/email-verification/confirm   メール認証完了

共通ルール
- データを変えるリクエストは未ログインでも CSRF を確認する（api/common/authentication.py）
- ログイン・新規登録でセッションと CSRF トークンを作り直す（Django の login()）。フロントは成功後に CSRF を取り直す
- ログイン前のゲストのカートは、ログイン後に会員のカートへ付け替える（services/cart.py）
"""
from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from ...common.exceptions import ApiError, Conflict
from ...common.throttles import IPRateThrottle
from ...serializers.public.auth import AuthUserSerializer, EmailVerificationConfirmSerializer, SigninSerializer
from ...services import email_verification, mail
from ...services.cart import merge_guest_cart


def already_authenticated():
    return Conflict("ALREADY_AUTHENTICATED", "既にログインしています。")


def login_and_merge_cart(request, user):
    """ログインしてセッションを作り直し、ゲストのときのカートを付け替える"""
    guest_session_key = request.session.session_key  # login() で作り直される前に控える
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    merge_guest_cart(guest_session_key, user)


def auth_response(message, user, status_code=status.HTTP_200_OK):
    return Response(
        {"message": message, "authenticated": True, "user": AuthUserSerializer(user).data},
        status=status_code,
    )


class CsrfView(APIView):
    """GET /api/v1/auth/csrf CSRFトークン取得

    CSRF Cookie を発行（必要なら作り直し）し、同じトークンを JSON でも返す。ログインセッションは作らない。
    """

    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"csrf_token": get_token(request)})


class SigninView(APIView):
    """POST /api/v1/auth/signin ログイン

    - 未登録・パスワード違い・利用停止・退会済みは、すべて同じ 401 INVALID_CREDENTIALS
    - メールアドレスが未確認でもログインできる
    - すでにログイン済みなら 409 ALREADY_AUTHENTICATED
    - 同じIPから1時間20回まで
    """

    permission_classes = [AllowAny]
    throttle_classes = [IPRateThrottle]
    throttle_scope = "signin"

    def post(self, request):
        if request.user.is_authenticated:
            raise already_authenticated()

        s = SigninSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user = authenticate(request, email=s.validated_data["email"], password=s.validated_data["password"])
        if user is None:
            # is_active=False（停止・退会）のユーザーも authenticate() は None を返す
            raise ApiError(status.HTTP_401_UNAUTHORIZED, "INVALID_CREDENTIALS",
                            "メールアドレスまたはパスワードが正しくありません。")

        login_and_merge_cart(request, user)
        return auth_response("ログインしました。", user)


class SessionView(APIView):
    """GET /api/v1/auth/session ログインチェック

    未ログインでも 200。Cookie なし・無効・期限切れ・利用停止・退会済みは {authenticated: false, user: null}。
    セッションの作成・延長はしない。CSRF 不要（GET）。
    """

    permission_classes = [AllowAny]

    def get(self, request):
        if not request.user.is_authenticated:
            return Response({"authenticated": False, "user": None})
        return Response({"authenticated": True, "user": AuthUserSerializer(request.user).data})


class SignoutView(APIView):
    """POST /api/v1/auth/signout ログアウト

    サーバー側のセッションを破棄し、セッション Cookie を削除する。未ログイン・期限切れでも 200。
    ただし CSRF は未ログインでも必須（失敗は 403）。
    """

    permission_classes = [AllowAny]

    def post(self, request):
        logout(request)
        return Response({"message": "ログアウトしました。"})


class ResendPerMinuteThrottle(UserRateThrottle):
    """同じユーザーは60秒に1回まで"""

    scope = "email_verification_resend_minute"


class ResendPerHourThrottle(UserRateThrottle):
    """同じユーザーは1時間に5回まで"""

    scope = "email_verification_resend_hour"


class EmailVerificationResendView(APIView):
    """POST /api/v1/auth/email-verification/resend 確認メール再送

    - ログイン中の本人宛てに送る（宛先はサーバーで決める。本文なし）
    - 確認済みでも同じ 202 を返し、送信はしない
    - 回数制限：同じユーザーは60秒に1回・1時間に5回、同じIPからは1時間10回
    """

    permission_classes = [IsAuthenticated]
    throttle_classes = [IPRateThrottle, ResendPerMinuteThrottle, ResendPerHourThrottle]
    throttle_scope = "email_verification_resend"

    def post(self, request):
        user = request.user
        if not user.email_verified:
            mail.send_email_verification(user, email_verification.make_token(user))
        return Response({"message": "必要な場合、確認メールの配送を受け付けました。"}, status=status.HTTP_202_ACCEPTED)


class EmailVerificationConfirmView(APIView):
    """POST /api/v1/auth/email-verification/confirm メール認証完了

    - ログイン不要（CSRF は必須）。自動ログインはしない
    - 無効・期限切れ（24時間）・使用済み・メールアドレス不一致は 400 INVALID_OR_EXPIRED_TOKEN
    """

    permission_classes = [AllowAny]

    def post(self, request):
        s = EmailVerificationConfirmSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        if email_verification.verify(s.validated_data["token"]) is None:
            raise ApiError(status.HTTP_400_BAD_REQUEST, "INVALID_OR_EXPIRED_TOKEN",
                            "認証リンクが無効、または有効期限が切れています。確認メールを再送してください。")
        return Response({"message": "メール認証が完了しました。", "email_verified": True})
