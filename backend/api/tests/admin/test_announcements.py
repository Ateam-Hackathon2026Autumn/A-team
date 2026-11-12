"""お知らせ管理 のテスト

テスト対象: api/views/admin/announcements.py
  - 一覧（status・audience・keyword）・詳細・作成・更新・削除。操作ログ。権限は「管理者」グループだけ
"""
from datetime import timedelta

from django.utils import timezone

from marche.models import AuditLog, Notice

from ..utils import ApiTestCase
from .test_producer_applications import make_staff

BASE = "/api/v1/admin/announcements"


class AdminAnnouncementTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.signin(make_staff("admin@example.com", "管理者").email)

    def test_list(self):
        now = timezone.now()
        draft = Notice.objects.create(title="下書き", body="b")
        scheduled = Notice.objects.create(title="来週の点検", body="b", published_at=now + timedelta(days=7))
        published = Notice.objects.create(title="年末年始の配送", body="b", audience="producer",
                                          published_at=now - timedelta(days=1))
        items = self.client.get(BASE).json()["items"]
        self.assertEqual([i["id"] for i in items], [published.id, scheduled.id, draft.id])
        self.assertEqual([i["status"] for i in items], ["published", "scheduled", "draft"])
        for query, expected in [({"status": "draft"}, [draft.id]), ({"status": "scheduled"}, [scheduled.id]),
                                ({"audience": "producer"}, [published.id]), ({"keyword": "点検"}, [scheduled.id])]:
            self.assertEqual([i["id"] for i in self.client.get(BASE, query).json()["items"]], expected, query)
        self.assertNotIn("body", items[0])
        self.assertEqual(self.client.get(BASE, {"status": "hidden"}).status_code, 400)

    def test_create_update_delete(self):
        res = self.post_json(BASE, {"title": "お知らせ", "body": "本文", "audience": "all", "publishedAt": None})
        self.assertEqual(res.status_code, 201, res.json())
        notice_id = res.json()["id"]
        self.assertEqual((res.json()["status"], res.json()["body"]), ("draft", "本文"))
        self.assertEqual(self.client.get("/api/v1/announcements").json()["items"], [])   # 下書きは公開側に出ない
        published_at = (timezone.now() - timedelta(minutes=1)).isoformat()
        res = self.patch_json(f"{BASE}/{notice_id}", {"publishedAt": published_at})
        self.assertEqual((res.status_code, res.json()["status"], res.json()["title"]), (200, "published", "お知らせ"))
        self.assertEqual(len(self.client.get("/api/v1/announcements").json()["items"]), 1)
        self.assertEqual(self.client.get(f"{BASE}/{notice_id}").json()["body"], "本文")
        self.assertEqual(self.delete_json(f"{BASE}/{notice_id}").status_code, 204)
        self.assertFalse(Notice.objects.exists())
        self.assertEqual(list(AuditLog.objects.order_by("id").values_list("action", flat=True)),
                         ["create", "update", "delete"])
        self.assertEqual(self.client.get(f"{BASE}/{notice_id}").status_code, 404)

    def test_validation_and_permission(self):
        for body, key in [({"title": "t", "body": "b", "audience": "all"}, "publishedAt"),
                          ({"title": "あ" * 101, "body": "b", "audience": "all", "publishedAt": None}, "title"),
                          ({"title": "t", "body": "b", "audience": "staff", "publishedAt": None}, "audience")]:
            res = self.post_json(BASE, body)
            self.assertEqual(res.status_code, 400, body)
            self.assertIn(key, res.json()["details"])
        notice = Notice.objects.create(title="t", body="b")
        self.assertEqual(self.patch_json(f"{BASE}/{notice.id}", {}).status_code, 400)
        self.post_json("/api/v1/admin/auth/signout")
        self.signin(make_staff("cs@example.com", "CS").email)
        self.assertEqual(self.client.get(BASE).status_code, 403)
