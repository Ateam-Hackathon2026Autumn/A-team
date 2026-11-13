"""問い合わせ のテスト

テスト対象: api/views/public/inquiries.py
  - 問い合わせ送信: POST /api/v1/inquiries
      ・ゲストは email 必須、会員は登録のメールアドレス（email を送ったら 400）
      ・orderId はログイン中の会員の自分の注文だけ
      ・受付メールを自動送信。CSRF を確認。同じIPから1時間5回まで（429）
"""
from django.core import mail
from django.core.cache import cache

from marche.models import Inquiry

from ..utils import ApiTestCase, make_order, make_user

URL = "/api/v1/inquiries"
BODY = {"category": "order", "subject": "届いていません", "body": "注文した野菜がまだ届きません。"}


class InquiryTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.user = make_user(email="buyer@example.com", last_name="佐藤", first_name="花子")

    def post(self, body):
        with self.captureOnCommitCallbacks(execute=True):
            return self.post_json(URL, body)

    def test_guest(self):
        res = self.post({**BODY, "email": " Guest@Example.com "})
        self.assertEqual(res.status_code, 201, res.json())
        inquiry = Inquiry.objects.get()
        self.assertEqual(res.json(), {"id": inquiry.id, "category": "order", "subject": "届いていません",
                                      "createdAt": res.json()["createdAt"]})
        self.assertEqual((inquiry.user, inquiry.order, inquiry.email, inquiry.status, inquiry.priority),
                         (None, None, "guest@example.com", "open", "medium"))
        self.assertEqual(mail.outbox[0].to, ["guest@example.com"])
        self.assertIn("お客様 様", mail.outbox[0].body)
        self.assertIn("注文した野菜がまだ届きません。", mail.outbox[0].body)
        self.assertIn("注文・配送", mail.outbox[0].body)

    def test_guest_errors(self):
        for body, key in [(BODY, "email"), ({**BODY, "email": "x"}, "email"),
                          ({**BODY, "email": "g@example.com", "orderId": make_order().id}, "orderId"),
                          ({**BODY, "email": "g@example.com", "category": "chat"}, "category"),
                          ({**BODY, "email": "g@example.com", "subject": "あ" * 101}, "subject"),
                          ({**BODY, "email": "g@example.com", "body": " "}, "body"),
                          ({**BODY, "email": "g@example.com", "body": "あ" * 5001}, "body"),
                          ({**BODY, "email": "g@example.com", "priority": "high"}, "priority")]:
            cache.clear()  # 回数制限（1時間5回）に当たらないように
            res = self.post(body)
            self.assertEqual(res.status_code, 400, body)
            self.assertIn(key, res.json()["details"], body)
        self.assertFalse(Inquiry.objects.exists())

    def test_member_with_order(self):
        self.signin(self.user.email)
        order = make_order(user=self.user)
        res = self.post({**BODY, "orderId": order.id})
        self.assertEqual(res.status_code, 201, res.json())
        inquiry = Inquiry.objects.get()
        self.assertEqual((inquiry.user, inquiry.order, inquiry.email), (self.user, order, "buyer@example.com"))
        self.assertIn("佐藤 花子 様", mail.outbox[0].body)
        self.assertEqual(self.post({**BODY, "orderId": None}).status_code, 201)

    def test_member_errors(self):
        self.signin(self.user.email)
        theirs = make_order(user=make_user(email="other@example.com"))
        guest = make_order(user=None, guest_email="g@example.com")
        for body, key in [({**BODY, "email": "buyer@example.com"}, "email"),
                          ({**BODY, "orderId": theirs.id}, "orderId"),
                          ({**BODY, "orderId": guest.id}, "orderId"),
                          ({**BODY, "orderId": 999999}, "orderId"),
                          ({**BODY, "orderId": 2 ** 63}, "orderId")]:
            res = self.post(body)
            self.assertEqual(res.status_code, 400, body)
            self.assertEqual(set(res.json()["details"]), {key}, body)

    def test_csrf_required(self):
        self.assertEqual(self.post_json(URL, {**BODY, "email": "g@example.com"}, csrf=False).status_code, 403)

    def test_rate_limit(self):
        for _ in range(5):
            self.assertEqual(self.post({**BODY, "email": "g@example.com"}).status_code, 201)
        res = self.post({**BODY, "email": "g@example.com"})
        self.assertEqual((res.status_code, res.json()["errorCode"]), (429, "RATE_LIMITED"))
