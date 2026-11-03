"""体験管理・予約枠・申込者（生産者ダッシュボード）のテスト"""
from datetime import timedelta

from django.core import mail
from django.utils import timezone

from marche.models import Experience, ExperienceImage, ExperienceSlot, Notification, Producer, PublishStatus, Reservation

from ..utils import ApiTestCase, make_experience, make_producer, make_reservation, make_slot, make_user

BASE = "/api/v1/dashboard/experiences"

VALID = {
    "title": "にんじん収穫体験",
    "description": "畑でにんじんを収穫します",
    "place": "山田農園（八王子市）",
    "priceAdult": 3000,
    "priceChild": 1500,
    "ageCondition": "小学生以上",
    "familyOk": True,
    "beginnerOk": True,
    "flow": [{"time": "10:00", "text": "集合"}, {"time": "10:30", "text": "収穫"}],
    "belongings": ["軍手", "長靴"],
    "notes": None,
    "cancelPolicy": "前日までにご連絡ください",
}


def future(days=7):
    return (timezone.now() + timedelta(days=days)).isoformat()


class ProducerTestCase(ApiTestCase):
    """承認済み・公開中の生産者でログインした状態から始める"""

    def setUp(self):
        super().setUp()
        self.producer = make_producer()
        self.client.force_login(self.producer.user)

    def suspend_producer(self):
        self.producer.publish_status = PublishStatus.SUSPENDED
        self.producer.save()


# =========================================================
# 権限
# =========================================================

class PermissionTests(ApiTestCase):
    def test_anonymous_is_401(self):
        res = self.client.get(BASE)
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.json()["errorCode"], "NOT_AUTHENTICATED")

    def test_not_producer_or_not_approved_is_403(self):
        pending = make_user(email="pending@example.com")
        make_producer(user=pending, approval=Producer.ApprovalStatus.PENDING, publish=PublishStatus.DRAFT)
        for user in (make_user(), pending):
            self.client.force_login(user)
            res = self.client.get(BASE)
            self.assertEqual(res.status_code, 403)
            self.assertEqual(res.json()["errorCode"], "FORBIDDEN")

    def test_other_producers_experience_is_404(self):
        mine, other = make_producer(), make_producer()
        theirs = make_experience(producer=other)
        slot = make_slot(theirs)
        self.client.force_login(mine.user)
        for url in (f"{BASE}/{theirs.id}", f"{BASE}/{theirs.id}/slots", f"{BASE}/{theirs.id}/applications"):
            self.assertEqual(self.client.get(url).status_code, 404, url)
        self.assertEqual(self.patch_json(f"{BASE}/{theirs.id}/slots/{slot.id}", {"capacity": 5}).status_code, 404)

    def test_slot_of_another_experience_is_404(self):
        producer = make_producer()
        exp1, exp2 = make_experience(producer), make_experience(producer)
        slot = make_slot(exp2)
        self.client.force_login(producer.user)
        self.assertEqual(self.delete_json(f"{BASE}/{exp1.id}/slots/{slot.id}").status_code, 404)


# =========================================================
# 体験一覧
# =========================================================

class ExperienceListTests(ProducerTestCase):
    def test_list_with_counts(self):
        old = make_experience(self.producer, title="古い体験")
        new = make_experience(self.producer, title="新しい体験", publish_status=PublishStatus.PUBLIC)
        make_experience(make_producer(), title="他の生産者の体験")
        past = make_slot(new, days=-3)
        soon = make_slot(new, days=3)
        make_slot(new, days=10)
        make_slot(new, days=1, status=ExperienceSlot.Status.CLOSED)  # 締切は次回開催にしない
        make_reservation(past)
        make_reservation(soon)
        make_reservation(soon, status=Reservation.Status.CANCELED)

        with self.assertNumQueries(5):  # セッション・ユーザー・生産者・件数・一覧
            res = self.client.get(BASE)
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual((body["total"], body["page"], body["pageSize"], body["totalPages"]), (2, 1, 20, 1))
        first, second = body["items"]
        self.assertEqual([first["id"], second["id"]], [new.id, old.id])  # 新しい順
        self.assertEqual(first["slotCount"], 4)
        self.assertEqual(first["applicationCount"], 3)  # キャンセルも含む
        self.assertEqual(first["nextStartAt"][:19], timezone.localtime(soon.start_at).isoformat()[:19])
        self.assertEqual((second["slotCount"], second["applicationCount"], second["nextStartAt"]), (0, 0, None))
        self.assertEqual(set(first), {"id", "title", "publishStatus", "prefectureId", "priceAdult", "priceChild",
                                        "slotCount", "applicationCount", "nextStartAt", "createdAt", "updatedAt"})

    def test_filter_and_paging(self):
        for i in range(3):
            make_experience(self.producer, title=f"下書き{i}")
        make_experience(self.producer, publish_status=PublishStatus.PRIVATE)
        body = self.client.get(BASE, {"publishStatus": "draft", "pageSize": 2, "page": 2}).json()
        self.assertEqual((body["total"], body["totalPages"], len(body["items"])), (3, 2, 1))
        body = self.client.get(BASE, {"page": 9}).json()  # 範囲外は空配列
        self.assertEqual((body["items"], body["total"]), ([], 4))

    def test_invalid_query_is_400(self):
        for query in ("search=abc", "page=0", "pageSize=101", "publishStatus=", "page=1&page=2"):
            res = self.client.get(f"{BASE}?{query}")
            self.assertEqual(res.status_code, 400, query)
            self.assertEqual(res.json()["errorCode"], "VALIDATION_ERROR")


# =========================================================
# 体験登録・詳細・更新・削除
# =========================================================

class ExperienceCreateTests(ProducerTestCase):
    def test_create(self):
        res = self.post_json(BASE, VALID)
        self.assertEqual(res.status_code, 201, res.content)
        body = res.json()
        self.assertEqual(set(body), {"id", "producerId", "publishStatus", "createdAt", "updatedAt"})
        self.assertEqual(body["publishStatus"], "draft")
        experience = Experience.objects.get(pk=body["id"])
        self.assertEqual(experience.producer, self.producer)
        self.assertEqual(experience.prefecture_id, self.producer.prefecture_id)  # 省略時は生産者の都道府県
        self.assertEqual(experience.flow, [{"time": "10:00", "text": "集合"}, {"time": "10:30", "text": "収穫"}])

    def test_public_requires_image(self):
        res = self.post_json(BASE, {**VALID, "publishStatus": "public"})
        self.assertEqual(res.status_code, 409)
        self.assertEqual(res.json()["errorCode"], "IMAGE_REQUIRED")
        self.assertFalse(Experience.objects.exists())

    def test_validation(self):
        cases = {
            "title": {**VALID, "title": "   "},
            "priceAdult": {**VALID, "priceAdult": -1},
            "prefectureId": {**VALID, "prefectureId": 999},
            "publishStatus": {**VALID, "publishStatus": "suspended"},  # 生産者は選べない
            "flow": {**VALID, "flow": [{"time": "25:00", "text": "集合"}]},
            "producerId": {**VALID, "producerId": 1},  # 定義にない項目
            "images": {**VALID, "images": [{"imageKey": "a.jpg"}]},  # 画像は準備中
        }
        for field, data in cases.items():
            res = self.post_json(BASE, data)
            self.assertEqual(res.status_code, 400, field)
            self.assertIn(field, "".join(res.json()["details"]), field)
        self.assertEqual(self.post_json(BASE, {**VALID, "images": []}).status_code, 201)  # 空配列は受け付ける

    def test_suspended_producer_cannot_create(self):
        self.suspend_producer()
        res = self.post_json(BASE, VALID)
        self.assertEqual(res.status_code, 409)
        self.assertEqual(res.json()["errorCode"], "PRODUCER_SUSPENDED")
        self.assertEqual(self.client.get(BASE).status_code, 200)  # 閲覧はできる

    def test_csrf_is_required(self):
        self.assertEqual(self.post_json(BASE, VALID, csrf=False).status_code, 403)


class ExperienceDetailTests(ProducerTestCase):
    def test_detail(self):
        experience = make_experience(self.producer, flow=[{"time": "10:00", "text": "集合"}])
        ExperienceImage.objects.create(experience=experience, image="experience_images/b.jpg", sort_order=1)
        ExperienceImage.objects.create(experience=experience, image="experience_images/a.jpg", sort_order=0)
        res = self.client.get(f"{BASE}/{experience.id}")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["flow"], [{"time": "10:00", "text": "集合"}])
        self.assertEqual([i["imageKey"] for i in body["images"]],
                         ["experience_images/a.jpg", "experience_images/b.jpg"])  # sort_order 順
        self.assertTrue(body["images"][0]["url"].endswith("experience_images/a.jpg"))
        self.assertNotIn("slots", body)

    def test_suspended_experience_can_be_viewed(self):
        experience = make_experience(self.producer, publish_status=PublishStatus.SUSPENDED)
        self.assertEqual(self.client.get(f"{BASE}/{experience.id}").json()["publishStatus"], "suspended")


class ExperienceUpdateTests(ProducerTestCase):
    def setUp(self):
        super().setUp()
        self.experience = make_experience(self.producer)
        self.url = f"{BASE}/{self.experience.id}"

    def test_update_only_sent_fields(self):
        res = self.patch_json(self.url, {"title": "新しいタイトル", "priceChild": None})
        self.assertEqual(res.status_code, 200, res.content)
        self.experience.refresh_from_db()
        self.assertEqual((self.experience.title, self.experience.price_child), ("新しいタイトル", None))
        self.assertEqual(self.experience.price_adult, 3000)

    def test_price_change_keeps_existing_reservations(self):
        reservation = make_reservation(make_slot(self.experience), total_amount=6000)
        self.assertEqual(self.patch_json(self.url, {"priceAdult": 5000}).status_code, 200)
        reservation.refresh_from_db()
        self.assertEqual(reservation.total_amount, 6000)

    def test_empty_body_and_null_are_400(self):
        self.assertEqual(self.patch_json(self.url, {}).status_code, 400)
        self.assertEqual(self.patch_json(self.url, {"title": None}).status_code, 400)

    def test_publish(self):
        res = self.patch_json(self.url, {"publishStatus": "public"})
        self.assertEqual(res.json()["errorCode"], "IMAGE_REQUIRED")
        ExperienceImage.objects.create(experience=self.experience, image="experience_images/a.jpg")
        res = self.patch_json(self.url, {"publishStatus": "public"})
        self.assertEqual(res.json()["publishStatus"], "public")

    def test_suspended_experience(self):
        self.experience.publish_status = PublishStatus.SUSPENDED
        self.experience.save()
        self.assertEqual(self.patch_json(self.url, {"title": "修正しました"}).status_code, 200)  # 内容は直せる
        res = self.patch_json(self.url, {"publishStatus": "private"})
        self.assertEqual(res.status_code, 409)
        self.assertEqual(res.json()["errorCode"], "CONTENT_SUSPENDED")

    def test_suspended_producer_cannot_update(self):
        self.suspend_producer()
        self.assertEqual(self.patch_json(self.url, {"title": "x"}).json()["errorCode"], "PRODUCER_SUSPENDED")


class ExperienceDeleteTests(ProducerTestCase):
    def test_delete(self):
        experience = make_experience(self.producer)
        make_slot(experience)
        res = self.delete_json(f"{BASE}/{experience.id}")
        self.assertEqual(res.status_code, 204)
        self.assertFalse(Experience.objects.exists())
        self.assertFalse(ExperienceSlot.objects.exists())

    def test_with_reservation_history_is_409(self):
        experience = make_experience(self.producer)
        make_reservation(make_slot(experience), status=Reservation.Status.CANCELED)
        res = self.delete_json(f"{BASE}/{experience.id}")
        self.assertEqual(res.status_code, 409)
        self.assertEqual(res.json()["errorCode"], "HAS_RESERVATIONS")


# =========================================================
# 体験申込者一覧
# =========================================================

class ApplicationListTests(ProducerTestCase):
    def setUp(self):
        super().setUp()
        self.experience = make_experience(self.producer)
        self.url = f"{BASE}/{self.experience.id}/applications"

    def test_list(self):
        slot1, slot2 = make_slot(self.experience, days=3), make_slot(self.experience, days=5)
        r1 = make_reservation(slot1, message="よろしくお願いします")
        r2 = make_reservation(slot2, status=Reservation.Status.CANCELED)
        body = self.client.get(self.url).json()
        self.assertEqual([i["id"] for i in body["items"]], [r2.id, r1.id])
        item = body["items"][1]
        self.assertEqual(item["slot"]["id"], slot1.id)
        self.assertEqual(item["user"], {"id": r1.user_id, "lastName": "山田", "firstName": "太郎", "isActive": True})
        self.assertEqual((item["representativeName"], item["phone"]), ("佐藤 花子", "09012345678"))
        self.assertNotIn("email", item["user"])

        body = self.client.get(self.url, {"slotId": slot1.id}).json()
        self.assertEqual([i["id"] for i in body["items"]], [r1.id])
        body = self.client.get(self.url, {"status": "canceled"}).json()
        self.assertEqual([i["id"] for i in body["items"]], [r2.id])

    def test_slot_of_other_experience_is_404(self):
        other_slot = make_slot(make_experience(self.producer))
        self.assertEqual(self.client.get(self.url, {"slotId": other_slot.id}).status_code, 404)

    def test_inactive_user_is_masked(self):
        reservation = make_reservation(make_slot(self.experience))
        reservation.user.is_active = False
        reservation.user.save()
        item = self.client.get(self.url).json()["items"][0]
        self.assertEqual(item["user"], {"id": reservation.user_id, "lastName": None, "firstName": None,
                                        "isActive": False})
        self.assertEqual((item["representativeName"], item["phone"], item["message"]), (None, None, None))

    def test_query_count(self):
        for _ in range(3):
            make_reservation(make_slot(self.experience, days=len(Reservation.objects.all()) + 1))
        with self.assertNumQueries(6):  # セッション・ユーザー・生産者・体験・件数・一覧（予約枠と会員は JOIN）
            self.client.get(self.url)


# =========================================================
# 予約枠
# =========================================================

class SlotListCreateTests(ProducerTestCase):
    def setUp(self):
        super().setUp()
        self.experience = make_experience(self.producer)
        self.url = f"{BASE}/{self.experience.id}/slots"

    def test_list(self):
        later = make_slot(self.experience, days=10)
        past = make_slot(self.experience, days=-1)
        full = make_slot(self.experience, days=3, capacity=2)
        make_reservation(full, adult_count=2)
        body = self.client.get(self.url).json()
        self.assertEqual([i["id"] for i in body["items"]], [past.id, full.id, later.id])  # 開催日時の順
        self.assertEqual((body["items"][1]["reservedCount"], body["items"][1]["remainingCapacity"]), (2, 0))

    def test_create(self):
        res = self.post_json(self.url, {"startAt": "2099-12-01T10:00:00+09:00", "durationMin": 120, "capacity": 8})
        self.assertEqual(res.status_code, 201, res.content)
        body = res.json()
        self.assertEqual((body["status"], body["reservedCount"], body["remainingCapacity"]), ("open", 0, 8))
        self.assertEqual(body["startAt"], "2099-12-01T10:00:00+09:00")

        res = self.post_json(self.url, {"startAt": "2099-12-01T01:00:00Z", "durationMin": 60, "capacity": 5})
        self.assertEqual(res.status_code, 409)  # 同じ瞬間（日本時間 10:00）
        self.assertEqual(res.json()["errorCode"], "DUPLICATE_SLOT")

    def test_create_validation(self):
        cases = {
            "startAt": {"startAt": "2099-12-01T10:00:00", "durationMin": 60, "capacity": 5},  # タイムゾーンなし
            "startAt ": {"startAt": "2000-01-01T10:00:00+09:00", "durationMin": 60, "capacity": 5},  # 過去
            "durationMin": {"startAt": future(), "durationMin": 0, "capacity": 5},
            "capacity": {"startAt": future(), "durationMin": 60, "capacity": 0},
            "status": {"startAt": future(), "durationMin": 60, "capacity": 5, "status": "canceled"},
            "reservedCount": {"startAt": future(), "durationMin": 60, "capacity": 5, "reservedCount": 3},
        }
        for field, data in cases.items():
            res = self.post_json(self.url, data)
            self.assertEqual(res.status_code, 400, field)
            self.assertIn(field.strip(), res.json()["details"], field)

    def test_suspended_producer_cannot_create(self):
        self.suspend_producer()
        res = self.post_json(self.url, {"startAt": future(), "durationMin": 60, "capacity": 5})
        self.assertEqual(res.json()["errorCode"], "PRODUCER_SUSPENDED")


class SlotUpdateTests(ProducerTestCase):
    def setUp(self):
        super().setUp()
        self.experience = make_experience(self.producer, title="にんじん収穫体験")
        self.slot = make_slot(self.experience, capacity=10)
        self.url = f"{BASE}/{self.experience.id}/slots/{self.slot.id}"

    def assert_conflict(self, data, code):
        res = self.patch_json(self.url, data)
        self.assertEqual(res.status_code, 409, res.content)
        self.assertEqual(res.json()["errorCode"], code)

    def test_update_without_reservations(self):
        res = self.patch_json(self.url, {"startAt": future(20), "durationMin": 90, "status": "closed"})
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual((res.json()["durationMin"], res.json()["status"]), (90, "closed"))

    def test_rules_with_reservations(self):
        make_reservation(self.slot, adult_count=4)
        self.assert_conflict({"startAt": future(20)}, "SLOT_TIME_LOCKED")
        self.assert_conflict({"durationMin": 30}, "SLOT_TIME_LOCKED")
        self.assertEqual(self.patch_json(self.url, {"durationMin": 120}).status_code, 200)  # 同じ値は可
        self.assert_conflict({"capacity": 3}, "CAPACITY_BELOW_RESERVED")
        self.assertEqual(self.patch_json(self.url, {"capacity": 4}).status_code, 200)

    def test_past_slot_is_409(self):
        self.slot.start_at = timezone.now() - timedelta(hours=1)
        self.slot.save()
        self.assert_conflict({"capacity": 20}, "SLOT_NOT_EDITABLE")

    def test_empty_body_is_400(self):
        self.assertEqual(self.patch_json(self.url, {}).status_code, 400)
        self.assertEqual(self.patch_json(self.url, {"status": "canceled", "capacity": 5}).status_code, 400)

    def test_cancel(self):
        active = make_reservation(self.slot, adult_count=2, child_count=1)
        canceled = make_reservation(self.slot, status=Reservation.Status.CANCELED)
        with self.captureOnCommitCallbacks(execute=True):
            res = self.patch_json(self.url, {"status": "canceled"})
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual((res.json()["status"], res.json()["reservedCount"]), ("canceled", 0))

        active.refresh_from_db()
        self.assertEqual(active.status, Reservation.Status.CANCELED)
        notification = Notification.objects.get()
        self.assertEqual((notification.user, notification.notification_type), (active.user, "reservation"))
        self.assertEqual(len(mail.outbox), 1)  # キャンセル済みだった予約者には送らない
        self.assertEqual(mail.outbox[0].to, [active.user.email])
        self.assertIn("にんじん収穫体験", mail.outbox[0].body)
        self.assertIn(active.reservation_no, mail.outbox[0].body)
        self.assertNotEqual(canceled.user, notification.user)

        self.assert_conflict({"status": "open"}, "SLOT_NOT_EDITABLE")  # 元に戻せない

    def test_suspended_producer_can_only_cancel(self):
        self.suspend_producer()
        self.assert_conflict({"capacity": 20}, "PRODUCER_SUSPENDED")
        self.assertEqual(self.patch_json(self.url, {"status": "canceled"}).status_code, 200)


class SlotDeleteTests(ProducerTestCase):
    def setUp(self):
        super().setUp()
        self.experience = make_experience(self.producer)

    def url(self, slot):
        return f"{BASE}/{self.experience.id}/slots/{slot.id}"

    def test_delete(self):
        slot = make_slot(self.experience)
        self.assertEqual(self.delete_json(self.url(slot)).status_code, 204)
        self.assertFalse(ExperienceSlot.objects.exists())

    def test_conflicts(self):
        past = make_slot(self.experience, days=-1)
        reserved = make_slot(self.experience)
        make_reservation(reserved, status=Reservation.Status.CANCELED)
        self.assertEqual(self.delete_json(self.url(past)).json()["errorCode"], "SLOT_NOT_EDITABLE")
        self.assertEqual(self.delete_json(self.url(reserved)).json()["errorCode"], "HAS_RESERVATIONS")
