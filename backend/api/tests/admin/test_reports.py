"""通報対応 のテスト

テスト対象: api/views/admin/reports.py
  - 通報一覧: GET /api/v1/admin/reports（初期値は open を古い順。対象の名前・公開状態・管理画面のパス）
  - 通報の対応更新: PATCH /api/v1/admin/reports/:reportId（handled_by は自分。open に戻すと空）
"""
from datetime import timedelta

from django.utils import timezone

from marche.models import AuditLog, Report

from ..utils import ApiTestCase, make_producer, make_product, make_user
from .test_producer_applications import make_staff

BASE = "/api/v1/admin/reports"


class AdminReportTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.staff = make_staff("cs@example.com", "CS")
        self.reporter = make_user(email="r@example.com", last_name="佐藤", first_name="花子")
        self.signin(self.staff.email)

    def report(self, target_type, target_id, days_ago=0, **kw):
        report = Report.objects.create(reporter=self.reporter, target_type=target_type, target_id=target_id,
                                       reason=kw.pop("reason", "spam"), **kw)
        Report.objects.filter(pk=report.pk).update(created_at=timezone.now() - timedelta(days=days_ago))
        return report

    def test_list(self):
        producer = make_producer(business_name="山田農園")
        product = make_product(producer, name="にんじん")
        first = self.report("product", product.id, days_ago=2, reason="fraud", detail="説明と違う")
        self.report("product", product.id, days_ago=1)
        gone = self.report("experience", 999999)
        on_producer = self.report("producer", producer.id)
        self.report("product", product.id, status="resolved")
        with self.assertNumQueries(10):  # 権限（3）＋SAVEPOINT・件数・一覧・RELEASE＋対象（商品・体験・生産者の種類ごとに1本）
            res = self.client.get(BASE)
        data = res.json()
        self.assertEqual([i["id"] for i in data["items"]][0], first.id)
        self.assertEqual(data["total"], 4)
        item = data["items"][0]
        self.assertEqual(item["target"], {"name": "にんじん", "publishStatus": "public",
                                          "adminPath": f"/admin/products/{product.id}"})
        self.assertEqual((item["reasonLabel"], item["detail"], item["sameTargetCount"]), ("詐欺・虚偽", "説明と違う", 2))
        self.assertEqual(item["reporter"], {"id": self.reporter.id, "name": "佐藤 花子", "email": "r@example.com"})
        by_id = {i["id"]: i for i in data["items"]}
        self.assertIsNone(by_id[gone.id]["target"])
        self.assertEqual(by_id[on_producer.id]["target"]["adminPath"], f"/admin/producers/{producer.id}")
        self.assertEqual(len(self.client.get(BASE, {"status": "resolved"}).json()["items"]), 1)
        self.assertEqual(self.client.get(BASE, {"targetType": "producer"}).json()["total"], 1)
        self.assertEqual(self.client.get(BASE, {"status": "closed"}).status_code, 400)

    def test_update(self):
        report = self.report("producer", make_producer().id)
        url = f"{BASE}/{report.id}"
        res = self.patch_json(url, {"status": "resolved"})
        self.assertEqual(res.status_code, 200, res.json())
        self.assertEqual((res.json()["status"], res.json()["handledBy"]),
                         ("resolved", {"id": self.staff.id, "name": "審査 花子"}))
        self.assertEqual(AuditLog.objects.get().detail, {"before": "open", "after": "resolved"})
        res = self.patch_json(url, {"status": "open"})
        self.assertEqual((res.json()["status"], res.json()["handledBy"]), ("open", None))
        for body in [{}, {"status": "closed"}, {"status": "dismissed", "handledBy": 1}]:
            self.assertEqual(self.patch_json(url, body).status_code, 400, body)
        self.assertEqual(self.patch_json(f"{BASE}/999999", {"status": "resolved"}).status_code, 404)

    def test_permission(self):
        self.post_json("/api/v1/admin/auth/signout")
        self.signin(make_staff("reviewer@example.com", "審査担当").email)
        self.assertEqual(self.client.get(BASE).status_code, 403)
