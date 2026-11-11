"""パスワード再設定 のテスト

テスト対象: api/views/public/auth.py（services/password_reset.py）
  - 申請: POST /api/v1/auth/password-reset（登録の有無にかかわらず 200。利用中の人にだけメール）
  - 再設定: POST /api/v1/auth/password-reset/confirm（無効・期限切れ・使用済みは 400 INVALID_OR_EXPIRED_TOKEN）
"""
import re
from datetime import datetime, timedelta
from unittest import mock
from urllib.parse import parse_qs, urlparse

from django.core import mail
from django.test import Client
from django.utils import timezone

from marche.models import User

from ...services import password_reset
from ..utils import PASSWORD, ApiTestCase, make_user

RESET = "/api/v1/auth/password-reset"
CONFIRM = "/api/v1/auth/password-reset/confirm"
NEW_PASSWORD = "BrandNewPass456!"


def link_params(body):
    url = re.search(r"http\S+", body).group(0)
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    return parsed.path, query["uid"][0], query["token"][0]


class PasswordResetRequestTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.user = make_user(email="taro@example.com")

    def test_sends_mail(self):
        res = self.post_json(RESET, {"email": " Taro@Example.com "})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(mail.outbox[0].to, ["taro@example.com"])
        path, uid, token = link_params(mail.outbox[0].body)
        self.assertEqual(path, "/password-reset/confirm")
        self.assertEqual(password_reset.find_user(uid, token), self.user)

    def test_same_response_without_mail(self):
        expected = self.post_json(RESET, {"email": "taro@example.com"}).json()
        mail.outbox.clear()
        suspended = make_user(email="stop@example.com", is_active=False)
        withdrawn = make_user(email="gone@example.com", deleted_at=timezone.now())
        for email in ["nobody@example.com", suspended.email, withdrawn.email]:
            res = self.post_json(RESET, {"email": email})
            self.assertEqual((res.status_code, res.json()), (200, expected))
        self.assertEqual(mail.outbox, [])

    def test_validation_and_rate_limit(self):
        for body in [{}, {"email": "x"}, {"email": "taro@example.com", "uid": "1"}]:
            self.assertEqual(self.post_json(RESET, body).status_code, 400)
        for _ in range(2):  # 400 も回数に数えるので、あと2回で5回
            self.assertEqual(self.post_json(RESET, {"email": "taro@example.com"}).status_code, 200)
        res = self.post_json(RESET, {"email": "taro@example.com"})
        self.assertEqual((res.status_code, res.json()["errorCode"]), (429, "RATE_LIMITED"))


class PasswordResetConfirmTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.user = make_user(email="taro@example.com")
        self.post_json(RESET, {"email": "taro@example.com"})
        _, self.uid, self.token = link_params(mail.outbox[0].body)
        mail.outbox.clear()

    def confirm(self, **kw):
        body = {"uid": self.uid, "token": self.token, "newPassword": NEW_PASSWORD, **kw}
        with self.captureOnCommitCallbacks(execute=True):
            return self.post_json(CONFIRM, body)

    def test_confirm(self):
        other_device = Client()
        other_device.force_login(self.user)  # ログインすると前のリンクは使えなくなるので、申請し直す
        self.assertTrue(other_device.get("/api/v1/auth/session").json()["authenticated"])
        self.assertEqual(self.confirm().status_code, 400)
        self.post_json(RESET, {"email": "taro@example.com"})
        _, self.uid, self.token = link_params(mail.outbox[0].body)
        mail.outbox.clear()
        res = self.confirm()
        self.assertEqual(res.status_code, 200, res.json())
        user = User.objects.get(pk=self.user.pk)
        self.assertTrue(user.check_password(NEW_PASSWORD))
        self.assertIsNotNone(user.email_verified_at)                     # リンクから来たので確認済みにする
        self.assertFalse(other_device.get("/api/v1/auth/session").json()["authenticated"])  # ほかの端末はログアウト
        self.assertFalse(self.client.get("/api/v1/auth/session").json()["authenticated"])  # 自動でログインしない
        self.assertEqual((mail.outbox[0].to, mail.outbox[0].subject),
                         (["taro@example.com"], "【つながるマルシェ】パスワードが再設定されました"))
        self.assertEqual(self.signin("taro@example.com", NEW_PASSWORD).status_code, 200)
        self.post_json("/api/v1/auth/signout")
        res = self.confirm(newPassword="AnotherPass789!")                 # 使用済み
        self.assertEqual((res.status_code, res.json()["errorCode"]), (400, "INVALID_OR_EXPIRED_TOKEN"))

    def test_invalid_tokens(self):
        for kw in [{"token": "abc-def"}, {"uid": "!!!"}, {"uid": "MTIzNDU2Nzg5MDEyMzQ1Njc4OTAx"}, {"uid": "MA"},
                   {"uid": "eA"}]:
            res = self.confirm(**kw)
            self.assertEqual((res.status_code, res.json()["errorCode"]), (400, "INVALID_OR_EXPIRED_TOKEN"), kw)
        self.assertTrue(User.objects.get(pk=self.user.pk).check_password(PASSWORD))

    def test_expired(self):
        later = datetime.now() + timedelta(hours=1, minutes=1)  # トークンの時刻は Django がローカル時刻（naive）で扱う
        with mock.patch("django.contrib.auth.tokens.PasswordResetTokenGenerator._now", return_value=later):
            res = self.confirm()
        self.assertEqual((res.status_code, res.json()["errorCode"]), (400, "INVALID_OR_EXPIRED_TOKEN"))

    def test_suspended_user(self):
        User.objects.filter(pk=self.user.pk).update(is_active=False)
        self.assertEqual(self.confirm().status_code, 400)

    def test_weak_password(self):
        for password in ["short", "taro@example.com"]:
            res = self.confirm(newPassword=password)
            self.assertEqual((res.status_code, set(res.json()["details"])), (400, {"newPassword"}))
        self.assertTrue(User.objects.get(pk=self.user.pk).check_password(PASSWORD))
        self.assertEqual(self.confirm().status_code, 200)               # 失敗してもトークンは使える

    def test_validation(self):
        for body in [{}, {"uid": self.uid, "token": self.token}, {"uid": self.uid, "token": "x" * 129,
                                                                  "newPassword": NEW_PASSWORD}]:
            self.assertEqual(self.post_json(CONFIRM, body).status_code, 400)
        res = self.post_json(CONFIRM, {"uid": self.uid, "token": self.token, "newPassword": NEW_PASSWORD}, csrf=False)
        self.assertEqual(res.status_code, 403)
