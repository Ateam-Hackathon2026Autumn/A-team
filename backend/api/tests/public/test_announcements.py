"""運営からのお知らせ のテスト

テスト対象: api/views/public/announcements.py
  - お知らせ一覧: GET /api/v1/announcements
  - お知らせ詳細: GET /api/v1/announcements/:announcementId
"""
from datetime import timedelta

from django.utils import timezone

from marche.models import Notice, Producer, PublishStatus

from ..utils import ApiTestCase, make_producer, make_user

URL = "/api/v1/announcements"


def notice(audience="all", days_ago=1, title="お知らせ"):
    published = timezone.now() - timedelta(days=days_ago) if days_ago is not None else None
    return Notice.objects.create(title=title, body="本文です", audience=audience, published_at=published)


class AnnouncementTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.all = notice("all", days_ago=3)
        self.consumer = notice("consumer", days_ago=2)
        self.producer = notice("producer", days_ago=1)
        notice("all", days_ago=-1)        # 予約公開（未来）
        notice("all", days_ago=None)      # 下書き

    def ids(self, res):
        return [item["id"] for item in res.json()["items"]]

    def test_list_for_consumers(self):
        res = self.client.get(URL)
        self.assertEqual(res.status_code, 200)
        self.assertEqual((self.ids(res), res.json()["total"]), ([self.consumer.id, self.all.id], 2))
        self.assertEqual(set(res.json()["items"][0]), {"id", "title", "audience", "publishedAt"})

    def test_list_for_producers(self):
        producer = make_producer(publish=PublishStatus.SUSPENDED)   # 掲載停止中でも見られる
        self.signin(producer.user.email)
        res = self.client.get(URL, {"audience": "producer"})
        self.assertEqual(self.ids(res), [self.producer.id, self.all.id])

    def test_producer_list_requires_producer(self):
        res = self.client.get(URL, {"audience": "producer"})
        self.assertEqual(res.status_code, 401)
        self.signin(make_user(email="member@example.com").email)
        self.assertEqual(self.client.get(URL, {"audience": "producer"}).status_code, 403)
        self.post_json("/api/v1/auth/signout")
        pending = make_producer(approval=Producer.ApprovalStatus.PENDING)
        self.assertEqual(self.signin(pending.user.email).status_code, 200)
        self.assertEqual(self.client.get(URL, {"audience": "producer"}).status_code, 403)
        self.assertEqual(self.client.get(URL, {"audience": "admin"}).status_code, 400)

    def test_detail(self):
        res = self.client.get(f"{URL}/{self.consumer.id}")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["body"], "本文です")

    def test_detail_not_found(self):
        future = Notice.objects.filter(published_at__gt=timezone.now()).first()
        draft = Notice.objects.filter(published_at__isnull=True).first()
        for notice_id in [future.id, draft.id, self.producer.id, 999999, 2 ** 63]:
            res = self.client.get(f"{URL}/{notice_id}")
            self.assertEqual((res.status_code, res.json()["errorCode"]), (404, "ANNOUNCEMENT_NOT_FOUND"))

    def test_producer_detail(self):
        self.signin(make_producer().user.email)
        self.assertEqual(self.client.get(f"{URL}/{self.producer.id}").status_code, 200)
