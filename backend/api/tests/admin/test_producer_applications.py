"""管理者ログイン・生産者審査 のテスト

テスト対象: api/views/admin/auth.py・api/views/admin/producer_applications.py
"""
from datetime import timedelta

from django.contrib.auth.models import Group
from django.core import mail
from django.utils import timezone

from marche.models import AuditLog, Notification, Producer, ProducerApplication, ProducerStory, PublishStatus

from ..utils import ApiTestCase, make_producer, make_user

Status = ProducerApplication.Status
LIST_URL = "/api/v1/admin/producer-applications"


def detail_url(application_id, action=""):
    return f"/api/v1/admin/producer-applications/{application_id}" + (f"/{action}" if action else "")


def make_staff(email, *groups):
    staff = make_user(email=email, is_staff=True, last_name="審査", first_name="花子")
    for name in groups:
        staff.groups.add(Group.objects.get_or_create(name=name)[0])
    return staff


def make_application(business_name="山田農園", status=Status.PENDING, submitted_at=None, **producer_fields):
    producer = make_producer(business_name=business_name, approval=Producer.ApprovalStatus.PENDING,
                             publish=PublishStatus.DRAFT, **producer_fields)
    Producer.objects.filter(pk=producer.pk).update(approval_status=status)
    return ProducerApplication.objects.create(producer=producer, status=status, application_reason="直接届けたい",
                                              submitted_at=submitted_at or timezone.now())


# =========================================================
# 管理者ログイン
# =========================================================

class AdminAuthTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.staff = make_staff("reviewer@example.com", "審査担当")

    def test_signin_session_signout(self):
        self.assertEqual(self.client.get("/api/v1/admin/auth/session").json(), {"authenticated": False, "user": None})
        res = self.post_json("/api/v1/admin/auth/signin", {"email": "reviewer@example.com", "password": "ExamplePass123!"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["user"], {"id": self.staff.id, "email": "reviewer@example.com",
                                              "lastName": "審査", "firstName": "花子", "groups": ["審査担当"]})
        self.assertTrue(self.client.get("/api/v1/admin/auth/session").json()["authenticated"])
        self.assertEqual(self.post_json("/api/v1/admin/auth/signin", {"email": "x@example.com", "password": "x"})
                         .json()["errorCode"], "ALREADY_AUTHENTICATED")
        self.assertEqual(self.post_json("/api/v1/admin/auth/signout").status_code, 200)
        self.assertFalse(self.client.get("/api/v1/admin/auth/session").json()["authenticated"])

    def test_non_staff_cannot_sign_in(self):
        make_user(email="member@example.com")
        for email, password in [("member@example.com", "ExamplePass123!"), ("reviewer@example.com", "wrong")]:
            res = self.post_json("/api/v1/admin/auth/signin", {"email": email, "password": password})
            self.assertEqual((res.status_code, res.json()["errorCode"]), (401, "INVALID_CREDENTIALS"))

    def test_member_session_is_not_admin(self):
        make_user(email="member@example.com")
        self.signin("member@example.com")
        self.assertFalse(self.client.get("/api/v1/admin/auth/session").json()["authenticated"])


# =========================================================
# 生産者審査
# =========================================================

class ReviewTestCase(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.reviewer = make_staff("reviewer@example.com", "審査担当")
        self.signin(self.reviewer.email)


class PermissionTests(ReviewTestCase):
    def test_groups(self):
        cases = [(make_staff("cs@example.com", "CS"), 403), (make_staff("admin@example.com", "管理者"), 200),
                 (make_user(email="member@example.com"), 403)]
        for user, expected in cases:
            with self.subTest(email=user.email):
                self.post_json("/api/v1/auth/signout")
                self.signin(user.email)
                self.assertEqual(self.client.get(LIST_URL).status_code, expected)
        self.post_json("/api/v1/auth/signout")
        self.assertEqual(self.client.get(LIST_URL).status_code, 401)


class ListDetailTests(ReviewTestCase):
    def test_list_defaults_to_pending_oldest_first(self):
        now = timezone.now()
        new = make_application("新しい農園", submitted_at=now)
        old = make_application("古い農園", submitted_at=now - timedelta(days=2))
        approved = make_application("承認済み", status=Status.APPROVED, submitted_at=now - timedelta(days=5))
        res = self.client.get(LIST_URL)
        self.assertEqual(res.status_code, 200)
        items = res.json()["items"]
        self.assertEqual([item["applicationId"] for item in items], [old.id, new.id])
        self.assertEqual(items[0]["producer"]["businessName"], "古い農園")
        self.assertEqual(set(items[0]["applicant"]), {"userId", "name", "email"})
        self.assertEqual([item["applicationId"] for item in self.client.get(LIST_URL, {"status": "approved"})
                          .json()["items"]], [approved.id])
        self.assertEqual([item["applicationId"] for item in self.client.get(LIST_URL, {"status": "all"})
                          .json()["items"]], [new.id, old.id, approved.id])
        self.assertEqual(self.client.get(LIST_URL, {"status": "done"}).status_code, 400)

    def test_detail_with_history(self):
        application = make_application()
        old = ProducerApplication.objects.create(
            producer=application.producer, status=Status.RETURNED, application_reason="", review_comment="直して",
            submitted_at=timezone.now() - timedelta(days=3))
        res = self.client.get(detail_url(application.id))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual((data["applicationId"], data["status"], data["applicationReason"]),
                         (application.id, "pending", "直接届けたい"))
        self.assertEqual(data["producer"]["businessName"], "山田農園")
        self.assertIn("phone", data["applicant"])
        self.assertEqual([(item["applicationId"], item["reviewComment"]) for item in data["history"]],
                         [(old.id, "直して")])
        self.assertEqual(self.client.get(detail_url(999999)).status_code, 404)


class ReviewActionTests(ReviewTestCase):
    def test_approve(self):
        application = make_application()
        with self.captureOnCommitCallbacks(execute=True):
            res = self.post_json(detail_url(application.id, "approve"))
        self.assertEqual(res.status_code, 200)
        self.assertEqual((res.json()["status"], res.json()["reviewerName"]), ("approved", "審査 花子"))
        producer = Producer.objects.get(pk=application.producer_id)
        self.assertEqual((producer.approval_status, producer.publish_status), ("approved", "draft"))
        self.assertIsNotNone(producer.approved_at)
        self.assertTrue(ProducerStory.objects.filter(producer=producer).exists())
        log = AuditLog.objects.get()
        self.assertEqual((log.action, log.target_type, log.target_id), ("approve", "producer_application",
                                                                         application.id))
        notification = Notification.objects.get(user=producer.user)
        self.assertEqual(notification.notification_type, "producer_review")
        self.assertEqual(len(mail.outbox), 1)

    def test_reject_and_return(self):
        for action, expected in [("reject", "rejected"), ("return", "returned")]:
            with self.subTest(action=action):
                application = make_application(business_name=f"{action}農園")
                res = self.post_json(detail_url(application.id, action), {"reviewComment": "品目を具体的に"})
                self.assertEqual(res.status_code, 200)
                self.assertEqual((res.json()["status"], res.json()["reviewComment"]), (expected, "品目を具体的に"))
                producer = Producer.objects.get(pk=application.producer_id)
                self.assertEqual(producer.approval_status, expected)
                self.assertIsNone(producer.approved_at)

    def test_comment_required_and_approve_has_no_body(self):
        application = make_application()
        for action, data in [("reject", {}), ("return", {"reviewComment": ""}),
                             ("return", {"reviewComment": "x" * 1001}), ("approve", {"reviewComment": "x"})]:
            with self.subTest(action=action, data=data):
                self.assertEqual(self.post_json(detail_url(application.id, action), data).status_code, 400)

    def test_only_latest_pending(self):
        reviewed = make_application(status=Status.RETURNED)
        res = self.post_json(detail_url(reviewed.id, "approve"))
        self.assertEqual((res.status_code, res.json()["errorCode"]), (409, "APPLICATION_NOT_PENDING"))
        # 古い pending（あとから新しい申請がある）も審査できない
        old_pending = make_application(business_name="二重")
        ProducerApplication.objects.create(producer=old_pending.producer, status=Status.PENDING, application_reason="",
                                           submitted_at=timezone.now() + timedelta(minutes=1))
        self.assertEqual(self.post_json(detail_url(old_pending.id, "approve")).status_code, 409)
        self.assertEqual(AuditLog.objects.count(), 0)

    def test_reapproval_keeps_first_approved_at(self):
        application = make_application()
        first_approved = timezone.now() - timedelta(days=100)
        Producer.objects.filter(pk=application.producer_id).update(approved_at=first_approved)
        self.post_json(detail_url(application.id, "approve"))
        self.assertEqual(Producer.objects.get(pk=application.producer_id).approved_at, first_approved)
