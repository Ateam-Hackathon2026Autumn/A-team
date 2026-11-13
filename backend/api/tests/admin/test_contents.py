"""生産者・商品・体験・求人・ストーリーの管理（掲載停止・再開） のテスト

テスト対象: api/views/admin/contents.py
  - 一覧: GET /api/v1/admin/{resource}（keyword・publishStatus・producerId。下書きや停止中も出す）
  - 詳細: GET /api/v1/admin/{resource}/:id（停止中なら suspension）
  - 掲載停止・再開: PATCH /api/v1/admin/{resource}/:id/status（suspend は reason 必須、resume は private に戻す）
"""
from django.core import mail
from django.utils import timezone

from marche.models import AuditLog, Notification, Producer, ProducerStory, PublishStatus, User

from ..utils import (ApiTestCase, make_experience, make_job, make_job_application, make_producer, make_product,
                     make_reservation, make_slot, make_user)
from .test_producer_applications import make_application, make_staff

BASE = "/api/v1/admin"


class ContentTestCase(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.staff = make_staff("reviewer@example.com", "審査担当")
        self.producer = make_producer(business_name="山田農園")
        self.other = make_producer(business_name="佐藤牧場")
        self.signin(self.staff.email)

    def patch_status(self, resource, obj_id, body):
        with self.captureOnCommitCallbacks(execute=True):
            return self.patch_json(f"{BASE}/{resource}/{obj_id}/status", body)


class ContentListTests(ContentTestCase):
    def ids(self, resource, **query):
        res = self.client.get(f"{BASE}/{resource}", query)
        self.assertEqual(res.status_code, 200, res.json())
        return [i["id"] for i in res.json()["items"]]

    def test_products(self):
        carrot = make_product(self.producer, name="にんじん")
        draft = make_product(self.producer, name="下書きのたまねぎ", publish_status=PublishStatus.DRAFT)
        milk = make_product(self.other, name="牛乳", publish_status=PublishStatus.SUSPENDED)
        self.assertEqual(self.ids("products"), [milk.id, draft.id, carrot.id])
        self.assertEqual(self.ids("products", keyword="たまねぎ"), [draft.id])
        self.assertEqual(self.ids("products", publishStatus="suspended"), [milk.id])
        self.assertEqual(self.ids("products", producerId=self.producer.id), [draft.id, carrot.id])
        item = self.client.get(f"{BASE}/products").json()["items"][2]
        self.assertEqual(item["producer"], {"id": self.producer.id, "businessName": "山田農園", "publishStatus": "public"})
        self.assertEqual((item["name"], item["price"], item["categoryName"]), ("にんじん", 1000, "野菜"))

    def test_producers(self):
        make_application(business_name="審査中の農園")
        self.assertEqual(self.ids("producers"), [self.other.id, self.producer.id])  # 承認済みだけ
        self.assertEqual(self.ids("producers", keyword=self.other.user.email), [self.other.id])
        item = self.client.get(f"{BASE}/producers", {"keyword": "山田農園"}).json()["items"][0]
        self.assertEqual((item["email"], item["userActive"], item["prefectureName"]),
                         (self.producer.user.email, True, "東京都"))
        self.assertEqual(self.client.get(f"{BASE}/producers", {"producerId": 1}).status_code, 400)

    def test_other_resources(self):
        experience = make_experience(self.producer, title="収穫体験")
        job = make_job(self.other, title="搾乳スタッフ")
        story = ProducerStory.objects.create(producer=self.producer, craft="こだわり")
        self.assertEqual(self.ids("experiences", keyword="収穫"), [experience.id])
        self.assertEqual(self.ids("jobs", producerId=self.other.id), [job.id])
        self.assertEqual(self.ids("stories", keyword="山田農園"), [story.id])
        for query in [{"publishStatus": "hidden"}, {"page": 0}, {"producerId": 0}]:
            self.assertEqual(self.client.get(f"{BASE}/products", query).status_code, 400)

    def test_permission(self):
        self.post_json("/api/v1/admin/auth/signout")
        self.assertEqual(self.client.get(f"{BASE}/products").status_code, 401)
        self.signin(make_staff("cs@example.com", "CS").email)
        self.assertEqual(self.client.get(f"{BASE}/products").status_code, 403)
        self.post_json("/api/v1/admin/auth/signout")
        self.signin(make_staff("admin@example.com", "管理者").email)
        self.assertEqual(self.client.get(f"{BASE}/stories").status_code, 200)


class ContentDetailTests(ContentTestCase):
    def test_details(self):
        product = make_product(self.producer)
        res = self.client.get(f"{BASE}/products/{product.id}")
        self.assertEqual((res.status_code, res.json()["images"], res.json()["suspension"]), (200, [], None))

        experience = make_experience(self.producer)
        buyer = make_user(email="buyer@example.com")
        make_reservation(make_slot(experience, days=3), user=buyer)
        make_reservation(make_slot(experience, days=-3), user=buyer)
        self.assertEqual(self.client.get(f"{BASE}/experiences/{experience.id}").json()["upcomingReservationCount"], 1)

        job = make_job(self.producer)
        make_job_application(job, user=buyer)
        make_job_application(job, user=make_user(email="b2@example.com"), status="rejected")
        self.assertEqual(self.client.get(f"{BASE}/jobs/{job.id}").json()["openApplicationCount"], 1)

        story = ProducerStory.objects.create(producer=self.producer)
        data = self.client.get(f"{BASE}/producers/{self.producer.id}").json()
        self.assertEqual((data["storyId"], data["counts"]), (story.id, {"products": 1, "experiences": 1, "jobs": 1}))
        self.assertEqual(self.client.get(f"{BASE}/stories/{story.id}").json()["producer"]["id"], self.producer.id)

    def test_not_found(self):
        pending = make_application(business_name="審査中の農園").producer
        for url in [f"{BASE}/products/999999", f"{BASE}/producers/{pending.id}", f"{BASE}/jobs/{2 ** 63}"]:
            res = self.client.get(url)
            self.assertEqual((res.status_code, res.json()["errorCode"]), (404, "NOT_FOUND"), url)


class ContentStatusTests(ContentTestCase):
    def test_suspend_and_resume_product(self):
        product = make_product(self.producer, name="にんじん")
        res = self.patch_status("products", product.id, {"action": "suspend", "reason": "表示が誤解を招くため"})
        self.assertEqual(res.status_code, 200, res.json())
        data = res.json()
        self.assertEqual(data["publishStatus"], "suspended")
        self.assertEqual((data["suspension"]["reason"], data["suspension"]["suspendedBy"]),
                         ("表示が誤解を招くため", {"id": self.staff.id, "name": "審査 花子"}))
        log = AuditLog.objects.get()
        self.assertEqual((log.action, log.target_type, log.target_id, log.detail),
                         ("suspend", "product", product.id,
                          {"reason": "表示が誤解を招くため", "before": "public", "after": "suspended"}))
        notice = Notification.objects.get(user=self.producer.user)
        self.assertEqual((notice.notification_type, notice.link_path),
                         ("listing_suspended", f"/dashboard/products/{product.id}"))
        self.assertIn("表示が誤解を招くため", mail.outbox[0].body)
        self.assertEqual(self.client.get(f"/api/v1/products/{product.id}").status_code, 404)  # 公開側から消える

        res = self.patch_status("products", product.id, {"action": "suspend", "reason": "もう一度"})
        self.assertEqual((res.status_code, res.json()["errorCode"]), (409, "STATUS_CONFLICT"))
        res = self.patch_status("products", product.id, {"action": "resume"})
        self.assertEqual((res.status_code, res.json()["publishStatus"], res.json()["suspension"]), (200, "private", None))
        self.assertEqual(Notification.objects.filter(notification_type="listing_resumed").count(), 1)
        res = self.patch_status("products", product.id, {"action": "resume"})
        self.assertEqual((res.status_code, res.json()["errorCode"]), (409, "STATUS_CONFLICT"))

    def test_each_resource(self):
        targets = [("producers", self.producer, "producer", "/dashboard"),
                   ("experiences", make_experience(self.producer), "experience", None),
                   ("jobs", make_job(self.producer), "job", None),
                   ("stories", ProducerStory.objects.create(producer=self.producer), "producer_story",
                    "/dashboard/story")]
        for resource, obj, target_type, link in targets:
            res = self.patch_status(resource, obj.id, {"action": "suspend", "reason": "規約違反"})
            self.assertEqual((res.status_code, res.json()["publishStatus"]), (200, "suspended"), resource)
            self.assertTrue(AuditLog.objects.filter(target_type=target_type, target_id=obj.id).exists())
            notice = Notification.objects.filter(user=self.producer.user).order_by("-id").first()
            self.assertEqual(notice.link_path, link or f"/dashboard/{resource}/{obj.id}")
        product = make_product(self.producer)
        self.assertEqual(Producer.objects.get(pk=self.producer.pk).publish_status, "suspended")
        self.assertEqual(self.client.get(f"/api/v1/products/{product.id}").status_code, 404)  # 生産者ごと消える

    def test_producer_resume_requires_active_user(self):
        self.patch_status("producers", self.producer.id, {"action": "suspend", "reason": "確認中"})
        User.objects.filter(pk=self.producer.user_id).update(is_active=False, deleted_at=timezone.now())
        res = self.patch_status("producers", self.producer.id, {"action": "resume"})
        self.assertEqual((res.status_code, res.json()["errorCode"]), (409, "USER_INACTIVE"))

    def test_withdrawn_producer_gets_no_notice(self):
        User.objects.filter(pk=self.producer.user_id).update(is_active=False)
        product = make_product(self.producer)
        self.assertEqual(self.patch_status("products", product.id, {"action": "suspend", "reason": "x"}).status_code, 200)
        self.assertFalse(Notification.objects.exists())

    def test_validation(self):
        product = make_product(self.producer)
        for body, key in [({"action": "suspend"}, "reason"), ({"action": "suspend", "reason": " "}, "reason"),
                          ({"action": "hide", "reason": "x"}, "action"), ({}, "action"),
                          ({"action": "suspend", "reason": "あ" * 1001}, "reason"),
                          ({"action": "resume", "publishStatus": "public"}, "publishStatus")]:
            res = self.patch_status("products", product.id, body)
            self.assertEqual(res.status_code, 400, body)
            self.assertIn(key, res.json()["details"], body)
        self.assertEqual(self.patch_status("products", 999999, {"action": "resume"}).status_code, 404)
        self.assertFalse(AuditLog.objects.exists())
