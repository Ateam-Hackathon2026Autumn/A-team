"""テストの共通部品

- ApiTestCase: 実際のブラウザと同じく CSRF を確認するクライアントを使うテストの基底クラス
- make_user / make_producer / make_product: テストデータを作る
"""
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from marche.models import Area, Category, Prefecture, Producer, Product, PublishStatus, ShippingSetting, User

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
