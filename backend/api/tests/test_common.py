"""共通部品（エラー形式・CSRF・401・回数制限・キャメルケース・no-store）のテスト

テスト用の view を下に定義し、ROOT_URLCONF をこのファイルに差し替えて確認する。
"""
from django.contrib.auth import authenticate
from django.core.cache import cache
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from django.test import TestCase, override_settings
from django.urls import path
from rest_framework import serializers
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.test import APIClient
from rest_framework.views import APIView

from api.common.exceptions import Conflict, csrf_failure
from api.common.serializers import StrictSerializer
from api.common.throttles import IPRateThrottle
from api.common.validators import PasswordPolicyValidator
from marche.models import User


class EchoSerializer(StrictSerializer):
    last_name = serializers.CharField(max_length=10)
    birth_date = serializers.DateField(required=False)


class PublicView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"category_id": request.query_params.get("category_id"), "is_ok": True})

    def post(self, request):
        s = EchoSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        return Response(s.validated_data)


class PrivateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"user_id": request.user.id})


class ConflictView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        raise Conflict("ALREADY_AUTHENTICATED", "既にログインしています。")


class NotFoundView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        raise Http404


class BrokenView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        raise RuntimeError("内部の詳細")


class TwoPerHourThrottle(IPRateThrottle):
    # テスト用に回数を小さくする（本番の回数は settings の DEFAULT_THROTTLE_RATES）
    THROTTLE_RATES = {"test": "2/hour"}


class ThrottledView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [TwoPerHourThrottle]
    throttle_scope = "test"

    def get(self, request):
        return Response({"ok": True})


urlpatterns = [
    path("api/v1/public", PublicView.as_view()),
    path("api/v1/private", PrivateView.as_view()),
    path("api/v1/conflict", ConflictView.as_view()),
    path("api/v1/not-found", NotFoundView.as_view()),
    path("api/v1/broken", BrokenView.as_view()),
    path("api/v1/throttled", ThrottledView.as_view()),
]


@override_settings(ROOT_URLCONF="api.tests.test_common")
class CommonApiTests(TestCase):
    def setUp(self):
        cache.clear()
        # 実際のブラウザと同じく CSRF を確認する
        self.client = APIClient(enforce_csrf_checks=True)

    def csrf_token(self):
        """GET で CSRF Cookie を受け取る代わりに、テスト用に Cookie とトークンを用意する"""
        from django.middleware.csrf import _get_new_csrf_string
        token = _get_new_csrf_string()
        self.client.cookies["csrftoken"] = token
        return token

    # --- CSRF -----------------------------------------------------------------

    def test_post_without_csrf_is_403_csrf_failed_even_when_anonymous(self):
        res = self.client.post("/api/v1/public", {"lastName": "山田"}, format="json")
        self.assertEqual(res.status_code, 403)
        self.assertEqual(res.json()["errorCode"], "CSRF_FAILED")

    def test_post_with_csrf_passes(self):
        token = self.csrf_token()
        res = self.client.post("/api/v1/public", {"lastName": "山田"}, format="json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(res.status_code, 200)

    def test_get_does_not_need_csrf(self):
        self.assertEqual(self.client.get("/api/v1/public").status_code, 200)

    def test_django_csrf_failure_view_returns_json(self):
        res = csrf_failure(None)
        self.assertEqual(res.status_code, 403)
        self.assertJSONEqual(res.content, {"errorCode": "CSRF_FAILED",
                                            "errorMsg": "リクエストを確認できませんでした。再度お試しください。"})

    # --- キャメルケース -------------------------------------------------------

    def test_camel_case_request_and_response(self):
        token = self.csrf_token()
        res = self.client.post("/api/v1/public", {"lastName": "山田", "birthDate": "1995-01-01"},
                                format="json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(res.json(), {"lastName": "山田", "birthDate": "1995-01-01"})

    def test_camel_case_query_params(self):
        self.assertEqual(self.client.get("/api/v1/public?categoryId=3").json(), {"categoryId": "3", "isOk": True})

    # --- エラー形式 -----------------------------------------------------------

    def test_validation_error_format(self):
        token = self.csrf_token()
        res = self.client.post("/api/v1/public", {"lastName": "あ" * 11}, format="json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(res.status_code, 400)
        body = res.json()
        self.assertEqual(body["errorCode"], "VALIDATION_ERROR")
        self.assertEqual(body["errorMsg"], "入力内容に誤りがあります。")
        self.assertEqual(list(body["details"]), ["lastName"])

    def test_unknown_field_is_rejected(self):
        token = self.csrf_token()
        res = self.client.post("/api/v1/public", {"lastName": "山田", "isAdmin": True},
                                format="json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()["details"], {"isAdmin": ["この項目は受け付けていません。"]})

    def test_broken_json_is_400(self):
        token = self.csrf_token()
        res = self.client.post("/api/v1/public", "{broken", content_type="application/json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()["errorCode"], "VALIDATION_ERROR")

    def test_not_authenticated_is_401_with_challenge(self):
        res = self.client.get("/api/v1/private")
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res["WWW-Authenticate"], 'Session realm="api"')
        self.assertEqual(res.json(), {"errorCode": "NOT_AUTHENTICATED", "errorMsg": "ログインしてください。"})

    def test_inactive_user_session_is_treated_as_anonymous(self):
        user = User.objects.create_user(email="a@example.com", password="Passw0rd!", last_name="山田", first_name="花子")
        self.client.force_login(user)
        self.assertEqual(self.client.get("/api/v1/private").status_code, 200)
        User.objects.filter(pk=user.pk).update(is_active=False)
        self.assertEqual(self.client.get("/api/v1/private").status_code, 401)

    def test_conflict(self):
        res = self.client.get("/api/v1/conflict")
        self.assertEqual(res.status_code, 409)
        self.assertEqual(res.json()["errorCode"], "ALREADY_AUTHENTICATED")

    def test_not_found(self):
        res = self.client.get("/api/v1/not-found")
        self.assertEqual(res.status_code, 404)
        self.assertEqual(res.json()["errorCode"], "NOT_FOUND")

    def test_unexpected_error_hides_details(self):
        with self.assertLogs("api.common.exceptions", level="ERROR"):
            res = self.client.get("/api/v1/broken")
        self.assertEqual(res.status_code, 500)
        self.assertEqual(res.json(), {"errorCode": "INTERNAL_SERVER_ERROR", "errorMsg": "サーバー内部エラーが発生しました。"})

    # --- no-store・回数制限 ---------------------------------------------------

    def test_no_store_header(self):
        self.assertEqual(self.client.get("/api/v1/public")["Cache-Control"], "no-store")
        self.assertEqual(self.client.get("/api/v1/private")["Cache-Control"], "no-store")

    def test_rate_limit(self):
        self.assertEqual(self.client.get("/api/v1/throttled").status_code, 200)
        self.assertEqual(self.client.get("/api/v1/throttled").status_code, 200)
        res = self.client.get("/api/v1/throttled")
        self.assertEqual(res.status_code, 429)
        self.assertEqual(res.json()["errorCode"], "RATE_LIMITED")
        self.assertGreaterEqual(int(res["Retry-After"]), 1)


class UserAccountRuleTests(TestCase):
    def test_email_is_trimmed_and_lowercased(self):
        user = User.objects.create_user(email="  Taro@Example.COM ", password="Passw0rd!",
                                        last_name="山田", first_name="太郎")
        self.assertEqual(user.email, "taro@example.com")
        # ログイン時も大文字・小文字を区別しない
        self.assertEqual(authenticate(email="TARO@example.com", password="Passw0rd!"), user)

    def test_password_policy(self):
        v = PasswordPolicyValidator()
        for ok in ("ExamplePass123!", "Aa1!aaaa"):
            v.validate(ok)
        for ng in ("examplepass123!", "EXAMPLEPASS123!", "ExamplePass!!!", "ExamplePass123",
                   "Aa1!aaa", "Aa1!" + "a" * 27, "Example Pass123!", "Ｅxample1!aa"):
            with self.assertRaises(DjangoValidationError, msg=ng):
                v.validate(ng)

    def test_email_verified_flag(self):
        user = User(email="a@example.com")
        self.assertFalse(user.email_verified)
