"""公開・会員・ゲスト向け の URL

api/urls/__init__.py から /api/v1/ に include する。
パスは api-spec.md のとおり（末尾スラッシュなし）。:id は <int:...> にする
"""
from django.urls import path

from ..views.public import auth, users

urlpatterns = [
    # 認証・ユーザー
    path("auth/csrf", auth.CsrfView.as_view(), name="auth-csrf"),
    path("auth/signin", auth.SigninView.as_view(), name="auth-signin"),
    path("auth/session", auth.SessionView.as_view(), name="auth-session"),
    path("auth/signout", auth.SignoutView.as_view(), name="auth-signout"),
    path("auth/email-verification/resend", auth.EmailVerificationResendView.as_view(),
        name="auth-email-verification-resend"),
    path("auth/email-verification/confirm", auth.EmailVerificationConfirmView.as_view(),
        name="auth-email-verification-confirm"),
    path("users", users.SignupView.as_view(), name="users-signup"),
]
