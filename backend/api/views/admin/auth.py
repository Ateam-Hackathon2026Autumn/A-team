"""管理者ログイン

認証: 公開・ゲスト可（ログインチェック・ログイン）。セッションは会員側と同じ仕組み
仕様: api-spec.md「管理者：認証・ダッシュボード」＋「7. 実装で決めたこと」（Notion には定義なし）
CSRF トークンは会員側と同じ GET /api/v1/auth/csrf で取る。

このファイルの API:
    - 管理者ログインチェック: GET /api/v1/admin/auth/session
        ・運営スタッフ（is_staff）でなければ {authenticated: false, user: null}（会員としてログイン中でも同じ）
        ・運営スタッフなら {authenticated: true, user: {id, email, lastName, firstName, groups}}
    - 管理者ログイン: POST /api/v1/admin/auth/signin
        ・{email, password}。未登録・パスワード違い・停止・運営スタッフでない人は、すべて同じ 401 INVALID_CREDENTIALS
        ・ログイン済みなら 409 ALREADY_AUTHENTICATED。同じIPから1時間20回まで（会員のログインと同じ回数制限）
    - 管理者ログアウト: POST /api/v1/admin/auth/signout
        ・セッションを破棄する。未ログインでも 200（CSRF は必須）
"""
from django.contrib.auth import authenticate, login, logout
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from ...common.exceptions import ApiError, Conflict
from ...common.throttles import IPRateThrottle
from ...serializers.admin.auth import AdminUserSerializer
from ...serializers.public.auth import SigninSerializer


def is_staff_user(user):
    return bool(user and user.is_authenticated and user.is_staff)


class AdminSessionView(APIView):
    """GET /api/v1/admin/auth/session"""

    permission_classes = [AllowAny]

    def get(self, request):
        if not is_staff_user(request.user):
            return Response({"authenticated": False, "user": None})
        return Response({"authenticated": True, "user": AdminUserSerializer(request.user).data})


class AdminSigninView(APIView):
    """POST /api/v1/admin/auth/signin"""

    permission_classes = [AllowAny]
    throttle_classes = [IPRateThrottle]
    throttle_scope = "signin"

    def post(self, request):
        if request.user.is_authenticated:
            raise Conflict("ALREADY_AUTHENTICATED", "既にログインしています。")
        serializer = SigninSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(request, email=serializer.validated_data["email"],
                            password=serializer.validated_data["password"])
        if not (user and user.is_staff):
            raise ApiError(status.HTTP_401_UNAUTHORIZED, "INVALID_CREDENTIALS",
                           "メールアドレスまたはパスワードが正しくありません。")
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        return Response({"message": "ログインしました。", "authenticated": True,
                         "user": AdminUserSerializer(user).data})


class AdminSignoutView(APIView):
    """POST /api/v1/admin/auth/signout"""

    permission_classes = [AllowAny]

    def post(self, request):
        logout(request)
        return Response({"message": "ログアウトしました。"})
