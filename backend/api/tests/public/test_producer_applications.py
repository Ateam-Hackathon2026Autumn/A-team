"""生産者申請 のテスト

テスト対象: api/views/public/producer_applications.py
  - 生産者登録申請: POST /api/v1/producer-applications
  - 申請状況: GET /api/v1/producer-applications/me
  - 再申請: PATCH /api/v1/producer-applications/me
"""
from datetime import timedelta

from django.utils import timezone

from marche.models import Producer, ProducerApplication, PublishStatus

from ..public.test_uploads import image_file
from ..utils import ApiTestCase, make_prefecture, make_producer, make_user

URL = "/api/v1/producer-applications"
ME_URL = "/api/v1/producer-applications/me"
Status = ProducerApplication.Status


def body(**overrides):
    data = {"businessName": "山田農園", "representativeName": "山田 太郎", "genre": "agriculture",
            "prefectureId": 13, "city": "八王子市", "productionItems": "野菜・果物", "intro": "季節の野菜を育てています",
            "acceptsExperience": True, "recruiting": False}
    data.update(overrides)
    return data


class ApplicationTestCase(ApiTestCase):
    def setUp(self):
        super().setUp()
        make_prefecture()
        self.user = make_user(email="farmer@example.com")
        self.signin(self.user.email)

    def apply(self, **overrides):
        return self.post_json(URL, body(**overrides))

    def set_latest_status(self, status, comment="生産品目を具体的に書いてください"):
        """管理者の審査の代わりに、最新の申請と生産者の状態を変える"""
        application = ProducerApplication.objects.order_by("-submitted_at", "-id").first()
        application.status = status
        application.review_comment = comment
        application.reviewed_at = timezone.now()
        application.save()
        Producer.objects.filter(pk=application.producer_id).update(approval_status=status)
        return application


# =========================================================
# 登録申請
# =========================================================

class CreateTests(ApplicationTestCase):
    def test_apply(self):
        key = self.post_multipart("/api/v1/uploads/images", {"image": image_file()}).json()["key"]
        res = self.apply(careerStartYear=2024, profileImage=key, applicationReason="  直接届けたいです  ")
        self.assertEqual(res.status_code, 201)
        body_ = res.json()
        producer = Producer.objects.get(user=self.user)
        application = ProducerApplication.objects.get(producer=producer)
        self.assertEqual(body_, {
            "message": "生産者登録申請を受け付けました。", "producerId": producer.id, "applicationId": application.id,
            "approvalStatus": "pending", "applicationStatus": "pending", "publishStatus": "draft",
            "isProducer": False, "submittedAt": body_["submittedAt"]})
        self.assertEqual((producer.business_name, producer.career_start_year, producer.profile_image.name),
                         ("山田農園", 2024, key))
        self.assertEqual(application.application_reason, "直接届けたいです")
        # ログインチェックでも審査中になる
        user = self.client.get("/api/v1/auth/session").json()["user"]
        self.assertEqual((user["isProducer"], user["producerApplicationStatus"]), (False, "pending"))

    def test_application_reason_is_optional(self):
        self.assertEqual(self.apply().status_code, 201)
        self.assertEqual(ProducerApplication.objects.get().application_reason, "")

    def test_invalid_body_is_400(self):
        other = make_user(email="other@example.com")
        next_year = timezone.localdate().year + 1
        cases = [
            {"businessName": "   "}, {"prefectureId": 99}, {"genre": "forestry"}, {"city": "x" * 51},
            {"careerStartYear": next_year}, {"foundedYear": 0}, {"profileImage": f"images/{other.id}/x.jpg"},
            {"approvalStatus": "approved"}, {"userId": other.id},
        ]
        for overrides in cases:
            with self.subTest(overrides=overrides):
                self.assertEqual(self.apply(**overrides).status_code, 400)
        res = self.post_json(URL, {k: v for k, v in body().items() if k != "intro"})
        self.assertEqual(res.status_code, 400)
        self.assertFalse(Producer.objects.exists())

    def test_already_applied_is_409(self):
        self.apply()
        res = self.apply()
        self.assertEqual((res.status_code, res.json()["errorCode"]), (409, "APPLICATION_ALREADY_PENDING"))
        self.set_latest_status(Status.RETURNED)
        self.assertEqual(self.apply().json()["errorCode"], "APPLICATION_RESUBMIT_REQUIRED")
        self.set_latest_status(Status.APPROVED)
        self.assertEqual(self.apply().json()["errorCode"], "PRODUCER_ALREADY_APPROVED")
        self.assertEqual(ProducerApplication.objects.count(), 1)

    def test_login_required(self):
        self.post_json("/api/v1/auth/signout")
        self.assertEqual(self.apply().status_code, 401)


# =========================================================
# 申請状況
# =========================================================

class StatusTests(ApplicationTestCase):
    def test_no_application_is_404(self):
        res = self.client.get(ME_URL)
        self.assertEqual((res.status_code, res.json()["errorCode"]), (404, "APPLICATION_NOT_FOUND"))

    def test_latest_application_and_current_producer(self):
        self.apply(applicationReason="最初の理由")
        self.set_latest_status(Status.RETURNED)
        res = self.client.get(ME_URL)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual((data["status"], data["reviewComment"], data["canResubmit"]),
                         ("returned", "生産品目を具体的に書いてください", True))
        self.assertIsNotNone(data["reviewedAt"])
        self.assertEqual(data["producer"]["businessName"], "山田農園")
        self.assertEqual(data["producer"]["applicationReason"], "最初の理由")
        self.assertEqual((data["producer"]["profileImage"], data["producer"]["profileImageUrl"]), (None, None))

    def test_can_resubmit(self):
        self.apply()
        self.assertFalse(self.client.get(ME_URL).json()["canResubmit"])  # 審査中
        self.set_latest_status(Status.REJECTED)
        self.assertTrue(self.client.get(ME_URL).json()["canResubmit"])  # 却下でも再申請できる
        Producer.objects.update(publish_status=PublishStatus.SUSPENDED)
        self.assertFalse(self.client.get(ME_URL).json()["canResubmit"])


# =========================================================
# 再申請
# =========================================================

class ResubmitTests(ApplicationTestCase):
    def setUp(self):
        super().setUp()
        self.apply(applicationReason="最初の理由")
        self.first = self.set_latest_status(Status.RETURNED)

    def resubmit(self, changes, application_id=None):
        return self.patch_json(ME_URL, {"applicationId": application_id or self.first.id, "changes": changes})

    def test_resubmit_creates_new_application(self):
        res = self.resubmit({"productionItems": "トマト・きゅうり"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["message"], "修正内容を保存し、再申請を受け付けました。")
        producer = Producer.objects.get()
        self.assertEqual((producer.production_items, producer.approval_status), ("トマト・きゅうり", "pending"))
        first, second = ProducerApplication.objects.order_by("id")
        self.assertEqual((first.status, first.review_comment), ("returned", "生産品目を具体的に書いてください"))
        self.assertEqual((second.status, second.application_reason, second.review_comment), ("pending", "最初の理由", None))
        self.assertEqual(res.json()["applicationId"], second.id)
        self.assertEqual(self.client.get(ME_URL).json()["applicationId"], second.id)

    def test_resubmit_after_reject(self):
        self.set_latest_status(Status.REJECTED)
        res = self.resubmit({"applicationReason": "体制を整えました"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(ProducerApplication.objects.order_by("-id").first().application_reason, "体制を整えました")

    def test_conflicts(self):
        self.resubmit({"intro": "直しました"})  # 2件目（pending）ができる
        res = self.resubmit({"intro": "もう一度"})  # 古い ID
        self.assertEqual((res.status_code, res.json()["errorCode"]), (409, "APPLICATION_CONFLICT"))
        latest = ProducerApplication.objects.order_by("-id").first()
        res = self.resubmit({"intro": "もう一度"}, application_id=latest.id)  # 審査中
        self.assertEqual((res.status_code, res.json()["errorCode"]), (409, "APPLICATION_NOT_RETURNED"))

    def test_suspended_producer_is_409(self):
        Producer.objects.update(publish_status=PublishStatus.SUSPENDED)
        res = self.resubmit({"intro": "直しました"})
        self.assertEqual((res.status_code, res.json()["errorCode"]), (409, "PRODUCER_SUSPENDED"))

    def test_others_application_is_404(self):
        other = make_producer()
        others_application = ProducerApplication.objects.create(
            producer=other, status=Status.RETURNED, application_reason="", submitted_at=timezone.now())
        res = self.resubmit({"intro": "x"}, application_id=others_application.id)
        self.assertEqual((res.status_code, res.json()["errorCode"]), (404, "APPLICATION_NOT_FOUND"))

    def test_invalid_body_is_400(self):
        for data in [{"applicationId": self.first.id, "changes": {}},
                     {"applicationId": self.first.id, "changes": {"businessName": ""}},
                     {"applicationId": self.first.id, "changes": {"status": "approved"}},
                     {"changes": {"intro": "x"}},
                     {"applicationId": self.first.id, "changes": {"intro": "x"}, "foo": 1}]:
            with self.subTest(data=data):
                self.assertEqual(self.patch_json(ME_URL, data).status_code, 400)

    def test_submitted_at_orders_latest(self):
        """申請日時がいちばん新しいものを最新とする"""
        self.resubmit({"intro": "直しました"})
        ProducerApplication.objects.filter(pk=self.first.pk).update(submitted_at=timezone.now() + timedelta(days=1))
        self.assertEqual(self.client.get(ME_URL).json()["applicationId"], self.first.id)
