"""通報 のテスト

テスト対象: api/views/public/reports.py
  - 通報: POST /api/v1/reports
      ・targetType は product・experience・job・producer（story・user は今は 400）
      ・公開中でない・存在しない → 404 TARGET_NOT_FOUND、自分のもの → 409 CANNOT_REPORT_OWN
      ・同じ対象を何度でも通報できる。同じ会員は1時間10回まで（429）
"""
from django.core import mail

from marche.models import PublishStatus, Report

from ..utils import ApiTestCase, make_experience, make_job, make_producer, make_product, make_user

URL = "/api/v1/reports"


class ReportTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.producer = make_producer(business_name="山田農園")
        self.product = make_product(self.producer)
        self.user = make_user(email="buyer@example.com")
        self.signin(self.user.email)

    def test_create(self):
        targets = [("product", self.product.id), ("experience", make_experience(self.producer, publish_status=PublishStatus.PUBLIC).id),
                   ("job", make_job(self.producer).id), ("producer", self.producer.id)]
        for target_type, target_id in targets:
            res = self.post_json(URL, {"targetType": target_type, "targetId": target_id, "reason": "fraud",
                                       "detail": " 価格が説明と違います "})
            self.assertEqual(res.status_code, 201, res.json())
            report = Report.objects.get(pk=res.json()["id"])
            self.assertEqual((report.reporter, report.target_type, report.target_id, report.reason, report.detail,
                              report.status),
                             (self.user, target_type, target_id, "fraud", "価格が説明と違います", "open"))
        res = self.post_json(URL, {"targetType": "product", "targetId": self.product.id, "reason": "other",
                                   "detail": ""})  # 同じ対象をもう一度
        self.assertEqual(res.status_code, 201)
        self.assertIsNone(Report.objects.get(pk=res.json()["id"]).detail)
        self.assertEqual(mail.outbox, [])

    def test_validation(self):
        base = {"targetType": "product", "targetId": self.product.id, "reason": "spam"}
        for body, key in [({**base, "targetType": "story"}, "targetType"),
                          ({**base, "targetType": "user", "targetId": self.producer.user_id}, "targetType"),
                          ({**base, "targetType": "order"}, "targetType"),
                          ({**base, "targetId": 0}, "targetId"), ({**base, "targetId": 2 ** 63}, "targetId"),
                          ({**base, "reason": "dislike"}, "reason"), ({**base, "detail": "あ" * 1001}, "detail"),
                          ({**base, "status": "resolved"}, "status")]:
            res = self.post_json(URL, body)
            self.assertEqual(res.status_code, 400, body)
            self.assertIn(key, res.json()["details"], body)
        self.assertFalse(Report.objects.exists())

    def test_not_found(self):
        hidden = make_product(self.producer, name="非公開", publish_status=PublishStatus.PRIVATE)
        pending = make_producer(user=make_user(email="new@example.com"), approval="pending")
        draft = make_experience(self.producer)
        for target_type, target_id in [("product", hidden.id), ("product", 999999), ("producer", pending.id),
                                       ("experience", draft.id), ("experience", self.product.id)]:
            res = self.post_json(URL, {"targetType": target_type, "targetId": target_id, "reason": "spam"})
            self.assertEqual((res.status_code, res.json()["errorCode"]), (404, "TARGET_NOT_FOUND"))

    def test_own(self):
        self.post_json("/api/v1/auth/signout")
        self.signin(self.producer.user.email)
        for target_type, target_id in [("product", self.product.id), ("producer", self.producer.id)]:
            res = self.post_json(URL, {"targetType": target_type, "targetId": target_id, "reason": "spam"})
            self.assertEqual((res.status_code, res.json()["errorCode"]), (409, "CANNOT_REPORT_OWN"))

    def test_login_and_rate_limit(self):
        body = {"targetType": "product", "targetId": self.product.id, "reason": "spam"}
        for _ in range(10):
            self.assertEqual(self.post_json(URL, body).status_code, 201)
        res = self.post_json(URL, body)
        self.assertEqual((res.status_code, res.json()["errorCode"]), (429, "RATE_LIMITED"))
        self.post_json("/api/v1/auth/signout")
        self.assertEqual(self.post_json(URL, body).status_code, 401)
