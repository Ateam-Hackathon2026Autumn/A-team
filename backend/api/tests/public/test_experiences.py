"""体験（公開側・申込） のテスト

テスト対象: api/views/public/experiences.py（services/reservations.py）
  - 体験一覧・詳細: GET /api/v1/experiences・GET /api/v1/experiences/:experienceId
  - 申込: POST /api/v1/experiences/:experienceId/applications
  - 申込状況・キャンセル: GET /api/v1/users/me/experience-applications・POST .../:applicationId/cancel
"""
from datetime import timedelta

from django.core import mail
from django.utils import timezone

from marche.models import Area, ExperienceImage, ExperienceSlot, Notification, Prefecture, PublishStatus, Reservation

from ..utils import ApiTestCase, make_experience, make_prefecture, make_producer, make_reservation, make_slot, make_user

URL = "/api/v1/experiences"
MY_URL = "/api/v1/users/me/experience-applications"


def public_experience(producer=None, **kw):
    kw.setdefault("publish_status", PublishStatus.PUBLIC)
    kw.setdefault("price_child", 1500)
    kw.setdefault("family_ok", True)
    experience = make_experience(producer, **kw)
    ExperienceImage.objects.create(experience=experience, image="experience_images/a.jpg", sort_order=0)
    return experience


class ExperienceListTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.producer = make_producer(business_name="山田農園")
        self.tokyo = make_prefecture()
        hokkaido_area = Area.objects.create(name="北海道", sort_order=1)
        self.hokkaido = Prefecture.objects.create(pk=1, area=hokkaido_area, name="北海道")

    def ids(self, res):
        return [item["id"] for item in res.json()["items"]]

    def test_list(self):
        old = public_experience(self.producer, title="古い体験")
        new = public_experience(self.producer, title="新しい体験", booking_deadline_hours=48)
        make_experience(self.producer, title="下書き")                                    # 非公開は出さない
        public_experience(make_producer(publish=PublishStatus.SUSPENDED))                  # 生産者が停止中
        make_slot(new, days=1)                       # 締め切り（48時間前）を過ぎている
        later = make_slot(new, days=5, capacity=2, reserved_count=2)   # 満席でも nextStartAt に入る
        make_slot(new, days=3, status=ExperienceSlot.Status.CANCELED)
        with self.assertNumQueries(5):  # 件数・一覧・日程（Prefetch）＋SAVEPOINT・RELEASE
            res = self.client.get(URL)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(self.ids(res), [new.id, old.id])
        item = res.json()["items"][0]
        self.assertEqual(set(item), {"id", "title", "prefectureId", "prefectureName", "areaId", "priceAdult",
                                     "priceChild", "familyOk", "beginnerOk", "thumbnailUrl", "producer",
                                     "nextStartAt"})
        self.assertEqual(item["nextStartAt"], timezone.localtime(later.start_at).isoformat())
        self.assertTrue(item["thumbnailUrl"].endswith("experience_images/a.jpg"))
        self.assertEqual(item["producer"]["businessName"], "山田農園")
        self.assertIsNone(res.json()["items"][1]["nextStartAt"])

    def test_filters(self):
        tokyo = public_experience(self.producer)
        hokkaido = public_experience(self.producer, prefecture=self.hokkaido)
        other = public_experience(make_producer(business_name="ほかの農園"))
        self.assertEqual(self.ids(self.client.get(URL, {"areaId": self.hokkaido.area_id})), [hokkaido.id])
        self.assertEqual(self.ids(self.client.get(URL, {"prefectureId": 13, "producerId": self.producer.id})),
                         [tokyo.id])
        self.assertEqual(self.ids(self.client.get(URL, {"producerId": other.producer_id})), [other.id])
        self.assertEqual(self.client.get(URL, {"areaId": 999}).json()["items"], [])
        self.assertEqual(self.client.get(URL, {"areaId": "abc"}).status_code, 400)


class ExperienceDetailTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.experience = public_experience(flow=[{"time": "10:00", "text": "集合"}], belongings=["軍手"])

    def test_detail(self):
        bookable = make_slot(self.experience, days=3)
        full = make_slot(self.experience, days=4, capacity=2, reserved_count=2)
        closed = make_slot(self.experience, days=0.5)                       # 締め切り（24時間前）を過ぎた
        make_slot(self.experience, days=-1)                                 # 過去は出さない
        make_slot(self.experience, days=6, status=ExperienceSlot.Status.CLOSED)
        res = self.client.get(f"{URL}/{self.experience.id}")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["flow"], [{"time": "10:00", "text": "集合"}])
        self.assertEqual(data["belongings"], ["軍手"])
        self.assertEqual(len(data["images"]), 1)
        slots = data["slots"]["items"]
        self.assertEqual([s["id"] for s in slots], [closed.id, bookable.id, full.id])
        self.assertEqual([s["bookable"] for s in slots], [False, True, False])
        self.assertEqual(slots[2]["remainingCapacity"], 0)
        self.assertEqual(slots[1]["bookingDeadlineAt"],
                         timezone.localtime(bookable.start_at - timedelta(hours=24)).isoformat())
        self.assertEqual(data["nextStartAt"], timezone.localtime(bookable.start_at).isoformat())

    def test_slot_paging(self):
        for day in range(2, 6):
            make_slot(self.experience, days=day)
        res = self.client.get(f"{URL}/{self.experience.id}", {"slotsPage": 2, "slotsPageSize": 3})
        self.assertEqual((res.json()["slots"]["total"], len(res.json()["slots"]["items"])), (4, 1))
        self.assertEqual(self.client.get(f"{URL}/{self.experience.id}", {"page": 1}).status_code, 400)

    def test_not_found(self):
        draft = make_experience()
        for experience_id in [draft.id, 999999, 2 ** 63]:
            res = self.client.get(f"{URL}/{experience_id}")
            self.assertEqual((res.status_code, res.json()["errorCode"]), (404, "EXPERIENCE_NOT_FOUND"))


class ApplicationTestCase(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.experience = public_experience(price_adult=3000, price_child=1500, title="にんじん収穫")
        self.slot = make_slot(self.experience, days=7, capacity=10)
        self.user = make_user(email="buyer@example.com")
        self.signin(self.user.email)

    def body(self, **kw):
        data = {"slotId": self.slot.id, "adultCount": 2, "childCount": 1, "infantCount": 1, "lastName": "佐藤",
                "firstName": "花子", "phone": "090-1234-5678", "message": "よろしくお願いします",
                "agreedToCancelPolicy": True, "eligibilityConfirmed": True, "expectedTotalAmount": 7500}
        data.update(kw)
        return data

    def apply(self, **kw):
        with self.captureOnCommitCallbacks(execute=True):
            return self.post_json(f"{URL}/{self.experience.id}/applications", self.body(**kw))


class ApplicationTests(ApplicationTestCase):
    def test_apply(self):
        res = self.apply()
        self.assertEqual(res.status_code, 201, res.json())
        data = res.json()
        reservation = Reservation.objects.get()
        self.assertEqual(data["id"], reservation.id)
        self.assertRegex(data["reservationNo"], r"^RV-\d{8}-\d{6}$")
        self.assertEqual((data["experienceId"], data["slotId"], data["status"], data["totalAmount"],
                          data["representativeName"], data["phone"]),
                         (self.experience.id, self.slot.id, "confirmed", 7500, "佐藤 花子", "09012345678"))
        self.slot.refresh_from_db()
        self.assertEqual(self.slot.reserved_count, 4)  # 未就学児も数える
        self.assertEqual(Notification.objects.get(user=self.user).link_path, "/mypage/experiences")
        self.assertEqual(Notification.objects.get(user=self.experience.producer.user).link_path,
                         f"/dashboard/experiences/{self.experience.id}/participants")
        self.assertEqual(sorted(m.to[0] for m in mail.outbox), sorted(["buyer@example.com",
                                                                       self.experience.producer.user.email]))
        self.assertIn("当日現地でお支払いください", next(m for m in mail.outbox if m.to == ["buyer@example.com"]).body)

    def test_requires_login(self):
        self.post_json("/api/v1/auth/signout")
        self.assertEqual(self.apply().status_code, 401)

    def test_validation(self):
        cases = [
            ({"adultCount": 0}, "adultCount"),
            ({"childCount": 100}, "childCount"),
            ({"adultCount": 50, "childCount": 30, "infantCount": 20}, "adultCount"),   # 合計99人まで
            ({"agreedToCancelPolicy": False}, "agreedToCancelPolicy"),
            ({"eligibilityConfirmed": False}, "eligibilityConfirmed"),
            ({"phone": "12"}, "phone"),
            ({"quoteToken": "x"}, "quoteToken"),
        ]
        for overrides, key in cases:
            res = self.apply(**overrides)
            self.assertEqual(res.status_code, 400, overrides)
            self.assertIn(key, res.json()["details"], overrides)
        self.assertFalse(Reservation.objects.exists())

    def test_children_rules(self):
        self.experience.price_child = None
        self.experience.save()
        res = self.apply(childCount=1, infantCount=0, expectedTotalAmount=6000)
        self.assertEqual((res.status_code, set(res.json()["details"])), (400, {"childCount"}))
        self.experience.price_child = 1500
        self.experience.family_ok = False
        self.experience.save()
        res = self.apply(childCount=0, infantCount=1, expectedTotalAmount=6000)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(self.apply(childCount=0, infantCount=0, expectedTotalAmount=6000).status_code, 201)

    def test_quote_changed(self):
        res = self.apply(expectedTotalAmount=7000)
        self.assertEqual((res.status_code, res.json()["errorCode"]), (409, "QUOTE_CHANGED"))

    def test_closed_slots(self):
        cases = [make_slot(self.experience, days=0.5), make_slot(self.experience, days=3, status="closed"),
                 make_slot(self.experience, days=3, status="canceled"), make_slot(self.experience, days=-1)]
        for slot in cases:
            res = self.apply(slotId=slot.id)
            self.assertEqual((res.status_code, res.json()["errorCode"]), (409, "BOOKING_CLOSED"))

    def test_capacity(self):
        self.slot.capacity = 5
        self.slot.reserved_count = 2
        self.slot.save()
        res = self.apply()  # 4人
        self.assertEqual((res.status_code, res.json()["errorCode"]), (409, "CAPACITY_EXCEEDED"))
        self.assertIn("残り3名", res.json()["errorMsg"])
        self.assertEqual(self.apply(childCount=0, infantCount=1, expectedTotalAmount=6000).status_code, 201)

    def test_already_applied(self):
        self.assertEqual(self.apply().status_code, 201)
        res = self.apply()
        self.assertEqual((res.status_code, res.json()["errorCode"]), (409, "ALREADY_APPLIED"))
        Reservation.objects.update(status="canceled")
        self.assertEqual(self.apply().status_code, 201)  # キャンセルのあとは申し込める

    def test_own_experience(self):
        self.post_json("/api/v1/auth/signout")
        self.signin(self.experience.producer.user.email)
        res = self.apply()
        self.assertEqual((res.status_code, res.json()["errorCode"]), (409, "CANNOT_APPLY_OWN"))

    def test_not_found(self):
        other_slot = make_slot(public_experience(title="別の体験"))
        res = self.apply(slotId=other_slot.id)
        self.assertEqual((res.status_code, res.json()["errorCode"]), (404, "SLOT_NOT_FOUND"))
        self.experience.publish_status = PublishStatus.PRIVATE
        self.experience.save()
        res = self.apply()
        self.assertEqual((res.status_code, res.json()["errorCode"]), (404, "EXPERIENCE_NOT_FOUND"))


class MyApplicationTests(ApplicationTestCase):
    def test_list(self):
        old = make_reservation(self.slot, user=self.user, status="attended")
        Reservation.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=1))
        new = make_reservation(make_slot(self.experience, days=10), user=self.user)
        make_reservation(self.slot)                                            # 他人の予約
        with self.assertNumQueries(7):  # セッション・ユーザー・公開中の体験・件数・一覧＋SAVEPOINT・RELEASE
            res = self.client.get(MY_URL)
        items = res.json()["items"]
        self.assertEqual([i["id"] for i in items], [new.id, old.id])
        self.assertEqual(items[0]["experience"], {"id": self.experience.id, "title": "にんじん収穫", "isPublic": True})
        self.assertEqual(set(items[0]["slot"]), {"id", "startAt", "durationMin", "status"})
        self.assertEqual((items[0]["cancellable"], items[1]["cancellable"]), (True, False))
        self.assertEqual(self.client.get(MY_URL, {"status": "attended"}).json()["total"], 1)

    def test_private_experience_hides_title(self):
        make_reservation(self.slot, user=self.user)
        self.experience.publish_status = PublishStatus.PRIVATE
        self.experience.save()
        item = self.client.get(MY_URL).json()["items"][0]
        self.assertEqual(item["experience"], {"id": self.experience.id, "title": None, "isPublic": False})


class CancelTests(ApplicationTestCase):
    def url(self, reservation_id):
        return f"{MY_URL}/{reservation_id}/cancel"

    def test_cancel(self):
        reservation_id = self.apply().json()["id"]
        mail.outbox.clear()
        with self.captureOnCommitCallbacks(execute=True):
            res = self.post_json(self.url(reservation_id))
        self.assertEqual((res.status_code, res.json()["status"], res.json()["cancellable"]), (200, "canceled", False))
        self.slot.refresh_from_db()
        self.assertEqual(self.slot.reserved_count, 0)
        self.assertEqual(mail.outbox[0].to, [self.experience.producer.user.email])
        res = self.post_json(self.url(reservation_id))
        self.assertEqual((res.status_code, res.json()["errorCode"]), (409, "CANCEL_NOT_ALLOWED"))

    def test_after_deadline(self):
        soon = make_slot(self.experience, days=0.5)
        reservation = make_reservation(soon, user=self.user)
        res = self.post_json(self.url(reservation.id))
        self.assertEqual((res.status_code, res.json()["errorCode"]), (409, "CANCEL_NOT_ALLOWED"))
        soon.refresh_from_db()
        self.assertEqual(soon.reserved_count, 2)

    def test_others_reservation_is_404(self):
        theirs = make_reservation(self.slot)
        for reservation_id in [theirs.id, 999999, 2 ** 63]:
            res = self.post_json(self.url(reservation_id))
            self.assertEqual((res.status_code, res.json()["errorCode"]), (404, "RESERVATION_NOT_FOUND"))

    def test_body_is_not_accepted(self):
        reservation = make_reservation(self.slot, user=self.user)
        self.assertEqual(self.post_json(self.url(reservation.id), {"reason": "x"}).status_code, 400)
