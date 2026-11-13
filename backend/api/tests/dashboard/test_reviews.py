"""レビュー確認・返信（生産者） のテスト

テスト対象: api/views/dashboard/reviews.py（services/reviews.py の reply_to_review）
  - レビュー一覧（生産者）: GET /api/v1/dashboard/reviews
  - レビュー返信: POST /api/v1/dashboard/reviews/:reviewId/reply
"""
from datetime import timedelta

from django.core import mail
from django.utils import timezone

from marche.models import Notification, ProductReview, PublishStatus

from ..public.test_reviews import review
from ..utils import ApiTestCase, make_producer, make_product, make_user

URL = "/api/v1/dashboard/reviews"


class DashboardReviewTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.producer = make_producer(business_name="山田農園")
        self.carrot = make_product(self.producer, name="にんじん")
        self.onion = make_product(self.producer, name="たまねぎ")
        self.buyer = make_user(email="buyer@example.com", first_name="花子")
        self.signin(self.producer.user.email)

    def test_list(self):
        old = review(self.buyer, self.carrot, reply="ありがとうございます")
        ProductReview.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=1))
        new = review(make_user(email="b@example.com", first_name="次郎"), self.onion)
        review(self.buyer, make_product(make_producer(business_name="ほかの農園")))  # 他の生産者の商品
        res = self.client.get(URL)
        data = res.json()
        self.assertEqual(([i["id"] for i in data["items"]], data["total"]), ([new.id, old.id], 2))
        self.assertEqual(data["items"][0]["product"], {"id": self.onion.id, "name": "たまねぎ"})
        self.assertEqual(data["items"][0]["reviewerName"], "次郎")
        self.assertNotIn("email", str(data))
        self.assertEqual([i["id"] for i in self.client.get(URL, {"unreplied": "true"}).json()["items"]], [new.id])
        self.assertEqual([i["id"] for i in self.client.get(URL, {"productId": self.carrot.id}).json()["items"]],
                         [old.id])

    def test_requires_producer(self):
        self.post_json("/api/v1/auth/signout")
        self.assertEqual(self.client.get(URL).status_code, 401)
        self.signin(self.buyer.email)
        self.assertEqual(self.client.get(URL).status_code, 403)

    def test_reply(self):
        target = review(self.buyer, self.carrot)
        url = f"{URL}/{target.id}/reply"
        with self.captureOnCommitCallbacks(execute=True):
            res = self.post_json(url, {"reply": "ありがとうございます"})
        self.assertEqual((res.status_code, res.json()["reply"]), (200, "ありがとうございます"))
        self.assertIsNotNone(res.json()["repliedAt"])
        notice = Notification.objects.get(user=self.buyer)
        self.assertEqual((notice.notification_type, notice.link_path), ("review_reply", f"/products/{self.carrot.id}"))
        self.assertEqual(mail.outbox, [])                                        # メールは送らない
        self.post_json(url, {"reply": "書き直しました"})                         # 上書き（通知は初回だけ）
        self.assertEqual(Notification.objects.filter(user=self.buyer).count(), 1)
        res = self.post_json(url, {"reply": ""})                                 # 空で削除
        self.assertEqual((res.json()["reply"], res.json()["repliedAt"]), (None, None))
        self.assertEqual(self.post_json(url, {"reply": "あ" * 1001}).status_code, 400)

    def test_reply_errors(self):
        theirs = review(self.buyer, make_product(make_producer(business_name="ほかの農園")))
        for review_id in [theirs.id, 999999, 2 ** 63]:
            res = self.post_json(f"{URL}/{review_id}/reply", {"reply": "x"})
            self.assertEqual((res.status_code, res.json()["errorCode"]), (404, "REVIEW_NOT_FOUND"))
        mine = review(self.buyer, self.carrot)
        self.producer.publish_status = PublishStatus.SUSPENDED
        self.producer.save()
        res = self.post_json(f"{URL}/{mine.id}/reply", {"reply": "x"})
        self.assertEqual((res.status_code, res.json()["errorCode"]), (409, "PRODUCER_SUSPENDED"))
        self.assertEqual(self.client.get(URL).status_code, 200)  # 掲載停止中でも見られる
