"""テストの共通部品

- ApiTestCase: 実際のブラウザと同じく CSRF を確認するクライアントを使うテストの基底クラス
- make_user / make_producer / make_product / make_experience / make_slot / make_reservation: テストデータを作る
"""
from datetime import timedelta

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from marche.models import (Area, Category, Experience, ExperienceSlot, Prefecture, Producer, Product, PublishStatus,
                            Reservation, ShippingSetting, User)

# テストでは S3 に接続しない
TEST_STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
PASSWORD = "ExamplePass123!"


@override_settings(STORAGES=TEST_STORAGES, MEDIA_URL="/media/")
class ApiTestCase(TestCase):
    def setUp(self):
        cache.clear()  # 回数制限のカウントをテストごとに消す
        self.client = APIClient(enforce_csrf_checks=True)

    def csrf(self):
        """GET /api/v1/auth/csrf でトークンを取る（Cookie も同時に受け取る）"""
        return self.client.get("/api/v1/auth/csrf").json()["csrfToken"]

    def post_json(self, url, data=None, csrf=True):
        headers = {"HTTP_X_CSRFTOKEN": self.csrf()} if csrf else {}
        return self.client.post(url, data or {}, format="json", **headers)
    
    def patch_json(self, url, data=None, csrf=True):
        headers = {"HTTP_X_CSRFTOKEN": self.csrf()} if csrf else {}
        return self.client.patch(url, data or {}, format="json", **headers)

    def delete_json(self, url, csrf=True):
        headers = {"HTTP_X_CSRFTOKEN": self.csrf()} if csrf else {}
        return self.client.delete(url, **headers)

    def signin(self, email, password=PASSWORD):
        return self.post_json("/api/v1/auth/signin", {"email": email, "password": password})


def make_prefecture(pk=13, name="東京都"):
    area, _ = Area.objects.get_or_create(name="関東", defaults={"sort_order": 3})
    pref, _ = Prefecture.objects.get_or_create(pk=pk, defaults={"area": area, "name": name})
    return pref


def make_user(email="taro@example.com", password=PASSWORD, **kw):
    kw.setdefault("last_name", "山田")
    kw.setdefault("first_name", "太郎")
    return User.objects.create_user(email=email, password=password, **kw)


def make_producer(user=None, approval=Producer.ApprovalStatus.APPROVED, publish=PublishStatus.PUBLIC, **kw):
    user = user or make_user(email=f"producer{User.objects.count()}@example.com")
    producer = Producer.objects.create(
        user=user,
        business_name=kw.pop("business_name", "山田農園"),
        representative_name="山田 太郎",
        genre=Producer.Genre.AGRICULTURE,
        prefecture=make_prefecture(),
        city="八王子市",
        production_items="野菜",
        intro="季節の野菜を育てています",
        approval_status=approval,
        publish_status=publish,
        **kw,
    )
    ShippingSetting.objects.create(producer=producer, temperature_zone="normal", shipping_fee=1000,
                                    lead_time_text="2〜4日で発送")
    return producer


def make_product(producer=None, name="にんじん", **kw):
    producer = producer or make_producer()
    category, _ = Category.objects.get_or_create(name="野菜", defaults={"sort_order": 1})
    fields = dict(volume="1kg", description="説明", price=1000, publish_status=PublishStatus.PUBLIC)
    fields.update(kw)
    return Product.objects.create(producer=producer, category=category,
                                  shipping_setting=producer.shipping_settings.first(), name=name, **fields)



def make_experience(producer=None, title="収穫体験", **kw):
    producer = producer or make_producer()
    fields = dict(description="にんじんを収穫します", place="山田農園", price_adult=3000,
                    cancel_policy="前日までにご連絡ください", publish_status=PublishStatus.DRAFT)
    fields.update(kw)
    return Experience.objects.create(producer=producer, prefecture=producer.prefecture, title=title, **fields)


def make_slot(experience=None, days=7, **kw):
    """days 日後に始まる予約枠（マイナスなら過去の枠）"""
    experience = experience or make_experience()
    fields = dict(duration_min=120, capacity=10, reserved_count=0)
    fields.update(kw)
    return ExperienceSlot.objects.create(experience=experience, start_at=timezone.now() + timedelta(days=days),
                                         **fields)


def make_reservation(slot, user=None, adult_count=2, status=Reservation.Status.CONFIRMED, **kw):
    """予約を作り、予約枠の reserved_count も人数分増やす（キャンセル済みは増やさない）"""
    user = user or make_user(email=f"guest{User.objects.count()}@example.com")
    fields = dict(child_count=0, infant_count=0, representative_name="佐藤 花子", phone="09012345678",
                  total_amount=3000 * adult_count, policy_agreed_at=timezone.now())
    fields.update(kw)
    reservation = Reservation.objects.create(
        reservation_no=f"R{Reservation.objects.count() + 1:08d}", slot=slot, user=user,
        adult_count=adult_count, status=status, **fields)
    if status != Reservation.Status.CANCELED:
        slot.reserved_count += adult_count + reservation.child_count + reservation.infant_count
        slot.save(update_fields=["reserved_count"])
    return reservation
