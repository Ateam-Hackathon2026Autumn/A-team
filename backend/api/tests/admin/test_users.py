"""ユーザー管理 のテスト

テスト対象: api/views/admin/users.py
  - ユーザー一覧: GET /api/v1/admin/users（運営スタッフは出さない。keyword・status・isProducer）
  - ユーザー詳細: GET /api/v1/admin/users/:userId（counts・activeTransactions・reports・operationHistory）
  - 利用停止・再開: PATCH /api/v1/admin/users/:userId/status
  - ユーザー削除: DELETE /api/v1/admin/users/:userId（匿名化。進行中の取引があれば 409）
"""
from django.core import mail
from django.test import Client
from django.utils import timezone

from marche.models import AuditLog, Order, Producer, Report, User

from ..utils import ApiTestCase, add_shipment, make_order, make_producer, make_product, make_user
from .test_producer_applications import make_staff

BASE = "/api/v1/admin/users"


class AdminUserTestCase(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.staff = make_staff("cs@example.com", "CS")
        self.user = make_user(email="hanako@example.com", last_name="佐藤", first_name="花子", phone="09011112222")
        self.signin(self.staff.email)

    def send(self, method, url, body):
        with self.captureOnCommitCallbacks(execute=True):
            return getattr(self, f"{method}_json")(url, body)


class AdminUserListTests(AdminUserTestCase):
    def ids(self, **query):
        res = self.client.get(BASE, query)
        self.assertEqual(res.status_code, 200, res.json())
        return [i["id"] for i in res.json()["items"]]

    def test_list(self):
        producer = make_producer(business_name="山田農園")
        stopped = make_user(email="stop@example.com", is_active=False)
        gone = make_user(email="gone@example.com", is_active=False, deleted_at=timezone.now())
        all_ids = self.ids()
        self.assertNotIn(self.staff.id, all_ids)
        self.assertEqual(set(all_ids), {self.user.id, producer.user_id, stopped.id, gone.id})
        self.assertEqual(self.ids(status="active"), [producer.user_id, self.user.id])
        self.assertEqual(self.ids(status="stopped"), [stopped.id])
        self.assertEqual(self.ids(status="withdrawn"), [gone.id])
        self.assertEqual(self.ids(isProducer="true"), [producer.user_id])
        self.assertEqual(self.ids(keyword="1111"), [self.user.id])
        self.assertEqual(self.ids(keyword="佐藤"), [self.user.id])
        item = next(i for i in self.client.get(BASE).json()["items"] if i["id"] == producer.user_id)
        self.assertEqual((item["isProducer"], item["producerId"], item["status"]), (True, producer.id, "active"))
        self.assertEqual(self.client.get(BASE, {"status": "deleted"}).status_code, 400)

    def test_permission(self):
        self.post_json("/api/v1/admin/auth/signout")
        self.signin(make_staff("reviewer@example.com", "審査担当").email)
        self.assertEqual(self.client.get(BASE).status_code, 403)


class AdminUserDetailTests(AdminUserTestCase):
    def test_detail(self):
        producer = make_producer(user=self.user, business_name="花子農園")
        make_order(user=self.user)
        make_order(user=self.user, payment_status=Order.PaymentStatus.PENDING)   # 支払い待ちは進行中の取引
        Report.objects.create(reporter=self.user, target_type="product", target_id=1, reason="spam")
        reporter = make_user(email="r@example.com")
        Report.objects.create(reporter=reporter, target_type="producer", target_id=producer.id, reason="fraud")
        Report.objects.create(reporter=reporter, target_type="user", target_id=self.user.id, reason="harassment")
        data = self.client.get(f"{BASE}/{self.user.id}").json()
        self.assertEqual(data["counts"], {"orders": 1, "reservations": 0, "jobApplications": 0, "reviews": 0})
        self.assertEqual(data["activeTransactions"], ["お支払い待ちの注文"])
        self.assertEqual(data["reports"], {"made": 1, "against": 2})
        self.assertEqual(data["producer"]["businessName"], "花子農園")
        self.assertEqual((data["prefectureName"], data["operationHistory"]), (None, []))
        self.assertNotIn("birthDate", data)

    def test_staff_and_missing_are_404(self):
        for user_id in [self.staff.id, 999999, 2 ** 63]:
            self.assertEqual(self.client.get(f"{BASE}/{user_id}").status_code, 404)


class AdminUserStatusTests(AdminUserTestCase):
    def test_stop_and_resume(self):
        producer = make_producer(user=self.user)
        device = Client()
        device.force_login(self.user)
        res = self.send("patch", f"{BASE}/{self.user.id}/status", {"action": "stop", "reason": "規約違反のため"})
        self.assertEqual(res.status_code, 200, res.json())
        self.assertEqual(res.json()["status"], "stopped")
        self.assertEqual(Producer.objects.get(pk=producer.pk).publish_status, "suspended")
        self.assertFalse(device.get("/api/v1/auth/session").json()["authenticated"])  # ほかの端末もログアウト
        self.assertEqual(mail.outbox[0].to, ["hanako@example.com"])
        self.assertIn("規約違反のため", mail.outbox[0].body)
        log = AuditLog.objects.get()
        self.assertEqual((log.action, log.target_type, log.detail["before"], log.detail["after"],
                          log.detail["producer_publish_status_before"]), ("stop", "user", "active", "stopped", "public"))
        self.assertEqual(len(res.json()["operationHistory"]), 1)

        res = self.send("patch", f"{BASE}/{self.user.id}/status", {"action": "stop", "reason": "再度"})
        self.assertEqual((res.status_code, res.json()["errorCode"]), (409, "STATUS_CONFLICT"))
        res = self.send("patch", f"{BASE}/{self.user.id}/status", {"action": "resume"})
        self.assertEqual((res.status_code, res.json()["status"]), (200, "active"))
        self.assertEqual(Producer.objects.get(pk=producer.pk).publish_status, "suspended")  # 掲載は戻さない
        self.post_json("/api/v1/admin/auth/signout")
        self.assertEqual(self.signin("hanako@example.com").status_code, 200)       # またログインできる

    def test_errors(self):
        url = f"{BASE}/{self.user.id}/status"
        for body, key in [({"action": "stop"}, "reason"), ({"action": "ban", "reason": "x"}, "action")]:
            res = self.send("patch", url, body)
            self.assertEqual((res.status_code, set(res.json()["details"])), (400, {key}))
        res = self.send("patch", url, {"action": "resume"})
        self.assertEqual((res.status_code, res.json()["errorCode"]), (409, "STATUS_CONFLICT"))
        User.objects.filter(pk=self.user.pk).update(is_active=False, deleted_at=timezone.now())
        res = self.send("patch", url, {"action": "stop", "reason": "x"})
        self.assertEqual((res.status_code, res.json()["errorCode"]), (409, "USER_WITHDRAWN"))
        self.assertEqual(self.send("patch", f"{BASE}/{self.staff.id}/status", {"action": "stop", "reason": "x"})
                         .status_code, 404)


class AdminUserDeleteTests(AdminUserTestCase):
    def test_delete(self):
        res = self.send("delete", f"{BASE}/{self.user.id}", {"reason": "本人からの依頼"})
        self.assertEqual(res.status_code, 204)
        user = User.objects.get(pk=self.user.pk)
        self.assertEqual((user.email, user.is_active), (f"deleted_{user.pk}@invalid", False))
        self.assertIsNotNone(user.deleted_at)
        self.assertEqual(mail.outbox[0].to, ["hanako@example.com"])
        self.assertEqual(AuditLog.objects.get().detail, {"reason": "本人からの依頼"})
        res = self.send("delete", f"{BASE}/{self.user.id}", {"reason": "もう一度"})
        self.assertEqual((res.status_code, res.json()["errorCode"]), (409, "USER_WITHDRAWN"))

    def test_active_transactions(self):
        producer = make_producer()
        add_shipment(make_order(user=self.user), producer, items=((make_product(producer), 1),))
        res = self.send("delete", f"{BASE}/{self.user.id}", {"reason": "依頼"})
        self.assertEqual((res.status_code, res.json()["errorCode"]), (409, "ACTIVE_TRANSACTIONS_EXIST"))
        self.assertIn("発送前", res.json()["errorMsg"])
        self.assertTrue(User.objects.get(pk=self.user.pk).is_active)

    def test_reason_required(self):
        for body in [{}, {"reason": ""}]:
            self.assertEqual(self.send("delete", f"{BASE}/{self.user.id}", body).status_code, 400)
        self.assertEqual(self.send("delete", f"{BASE}/{self.staff.id}", {"reason": "x"}).status_code, 404)
