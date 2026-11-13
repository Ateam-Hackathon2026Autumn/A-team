"""セッション認証と CSRF の確認

DRF 標準の SessionAuthentication との違い:
1. 未ログインのリクエストにも CSRF を確認する（ゲストも使うカート・注文・新規登録・ログインのため）
   GET などの安全なメソッドは確認しない
2. CSRF エラーを CsrfFailed（errorCode: CSRF_FAILED）にする
3. 未ログインのとき 403 ではなく 401 と WWW-Authenticate: Session realm="api" を返す

利用停止・退会済み（is_active=False）のユーザーは、Django の ModelBackend が
既存のセッションでも未ログイン扱いにする。

CSRF を確認しないAPI（Stripe の Webhook）は、view で authentication_classes = [] にする。
"""
from django.middleware.csrf import CsrfViewMiddleware
from rest_framework import authentication

from .exceptions import SESSION_CHALLENGE, CsrfFailed


class _CSRFCheck(CsrfViewMiddleware):
    def _reject(self, request, reason):
        # 呼び出し元に理由を返すだけにする（レスポンスは exception_handler で作る）
        return reason


class SessionAuthentication(authentication.SessionAuthentication):
    def authenticate(self, request):
        # ログインの有無にかかわらず、データを変えるリクエストは CSRF を確認する
        self.enforce_csrf(request)

        user = getattr(request._request, "user", None)
        if not user or not user.is_active:
            return None
        return (user, None)

    def enforce_csrf(self, request):
        def dummy_get_response(request):  # pragma: no cover
            return None

        check = _CSRFCheck(dummy_get_response)
        check.process_request(request)
        reason = check.process_view(request, None, (), {})
        if reason:
            raise CsrfFailed(f"CSRF Failed: {reason}")

    def authenticate_header(self, request):
        # これを返すと DRF は未ログインを 401 にする
        return SESSION_CHALLENGE
