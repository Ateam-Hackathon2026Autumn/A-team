"""問い合わせ対応 のテスト

テスト対象: api/views/admin/inquiries.py
  - 問い合わせ一覧: GET /api/v1/admin/inquiries（初期値は open・in_progress を優先度の高い順・古い順）
  - 問い合わせ詳細: GET /api/v1/admin/inquiries/:inquiryId（対応メモの履歴）
  - 問い合わせ更新: PATCH /api/v1/admin/inquiries/:inquiryId（status・priority・assigneeId・note）
"""
from datetime import timedelta

from django.core import mail
from django.utils import timezone

from marche.models import AuditLog, Inquiry, InquiryNote

from ..utils import ApiTestCase, make_order, make_user
from .test_producer_applications import make_staff

BASE = "/api/v1/admin/inquiries"


def make_inquiry(subject="届かない", days_ago=0, **kw):
    inquiry = Inquiry.objects.create(email=kw.pop("email", "guest@example.com"), category=kw.pop("category", "order"),
                                     subject=subject, body="本文です", **kw)
    Inquiry.objects.filter(pk=inquiry.pk).update(created_at=timezone.now() - timedelta(days=days_ago))
    return inquiry


class AdminInquiryTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.staff = make_staff("cs@example.com", "CS")
        self.signin(self.staff.email)

    def ids(self, **query):
        res = self.client.get(BASE, query)
        self.assertEqual(res.status_code, 200, res.json())
        return [i["id"] for i in res.json()["items"]]

    def test_list(self):
        low_old = make_inquiry(priority="low", days_ago=5)
        mid_old = make_inquiry(days_ago=3)
        mid_new = make_inquiry(days_ago=1, status="in_progress", assignee=self.staff)
        high = make_inquiry(priority="high", category="refund", subject="返金されない", email="taro@example.com")
        closed = make_inquiry(status="closed")
        self.assertEqual(self.ids(), [high.id, mid_old.id, mid_new.id, low_old.id])
        self.assertEqual(self.ids(status="closed"), [closed.id])
        self.assertEqual(len(self.ids(status="open,in_progress,closed")), 5)
        self.assertEqual(self.ids(assigneeId="me"), [mid_new.id])
        self.assertEqual(self.ids(assigneeId=str(self.staff.id)), [mid_new.id])
        self.assertEqual(self.ids(keyword="taro"), [high.id])
        self.assertEqual(self.ids(keyword=str(low_old.id)), [low_old.id])
        self.assertEqual(self.ids(category="refund"), [high.id])
        item = self.client.get(BASE, {"assigneeId": "me"}).json()["items"][0]
        self.assertEqual(item["assignee"], {"id": self.staff.id, "name": "審査 花子"})
        for query in [{"status": "done"}, {"status": ","}, {"assigneeId": "you"}, {"priority": "urgent"}]:
            self.assertEqual(self.client.get(BASE, query).status_code, 400, query)

    def test_detail_and_update(self):
        buyer = make_user(email="buyer@example.com", last_name="佐藤", first_name="花子")
        order = make_order(user=buyer)
        inquiry = make_inquiry(user=buyer, order=order, email=buyer.email)
        other = make_staff("admin@example.com", "管理者")
        url = f"{BASE}/{inquiry.id}"
        res = self.patch_json(url, {"status": "in_progress", "assigneeId": other.id, "note": "注文を確認中"})
        self.assertEqual(res.status_code, 200, res.json())
        data = res.json()
        self.assertEqual((data["status"], data["assignee"]["id"], data["body"]), ("in_progress", other.id, "本文です"))
        self.assertEqual((data["user"], data["order"]), ({"id": buyer.id, "name": "佐藤 花子"},
                                                         {"id": order.id, "orderNo": order.order_no}))
        self.assertEqual([(n["body"], n["author"]["id"]) for n in data["notes"]], [("注文を確認中", self.staff.id)])
        self.patch_json(url, {"note": "返信済み"})
        res = self.patch_json(url, {"status": "closed", "assigneeId": None, "priority": "low"})
        self.assertEqual((res.json()["status"], res.json()["assignee"], len(res.json()["notes"])), ("closed", None, 2))
        self.assertEqual(self.patch_json(url, {"status": "open"}).json()["status"], "open")   # 閉じても戻せる
        log = AuditLog.objects.filter(target_type="inquiry").order_by("id").first()
        self.assertEqual((log.detail["before"]["status"], log.detail["after"]["assignee_id"], log.detail["note_added"]),
                         ("open", other.id, True))
        self.assertEqual(mail.outbox, [])
        self.assertEqual(self.client.get(url).json()["notes"][1]["body"], "返信済み")

    def test_update_errors(self):
        inquiry = make_inquiry()
        reviewer = make_staff("reviewer@example.com", "審査担当")
        customer = make_user(email="c@example.com")
        url = f"{BASE}/{inquiry.id}"
        for body, key in [({}, "nonFieldErrors"), ({"assigneeId": reviewer.id}, "assigneeId"),
                          ({"assigneeId": customer.id}, "assigneeId"), ({"note": "あ" * 2001}, "note"),
                          ({"status": "done"}, "status"), ({"email": "x@example.com"}, "email")]:
            res = self.patch_json(url, body)
            self.assertEqual(res.status_code, 400, body)
            self.assertIn(key, res.json()["details"], body)
        self.assertFalse(InquiryNote.objects.exists())
        self.assertEqual(self.client.get(f"{BASE}/999999").status_code, 404)
        self.assertEqual(self.patch_json(f"{BASE}/999999", {"status": "closed"}).status_code, 404)
