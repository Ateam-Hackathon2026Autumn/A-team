"""テストの共通部品

- ApiTestCase: 実際のブラウザと同じく CSRF を確認するクライアントを使うテストの基底クラス
  （post_json / patch_json / put_json / delete_json / post_multipart）
- make_user / make_producer / make_product / make_experience / make_slot / make_reservation / make_order /
  add_shipment: テストデータを作る
"""
import atexit
import shutil
import tempfile
from datetime import timedelta

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from marche.models import (Area, Category, Experience, ExperienceSlot, Order, OrderItem, OrderShipment, Prefecture,
                            Producer, Product, PublishStatus, Reservation, ShippingSetting, User)

# テストでは S3 に接続しない。アップロードしたファイルは一時フォルダーに置き、テストが終わったら消す
TEST_MEDIA_ROOT = tempfile.mkdtemp(prefix="marche-test-media-")
atexit.register(shutil.rmtree, TEST_MEDIA_ROOT, ignore_errors=True)
TEST_STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
PASSWORD = "ExamplePass123!"


@override_settings(STORAGES=TEST_STORAGES, MEDIA_URL="/media/", MEDIA_ROOT=TEST_MEDIA_ROOT)
class ApiTestCase(TestCase):
    def setUp(self):
        cache.clear()  # 回数制限のカウントをテストごとに消す
        self.client = APIClient(enforce_csrf_checks=True)

    def csrf(self):
        """GET /api/v1/auth/csrf でトークンを取る（Cookie も同時に受け取る）"""
        return self.client.get("/api/v1/auth/csrf").json()["csrfToken"]

    def post_json(self, url, data=None, csrf=True, **extra):
        """extra: 追加のヘッダー（例: HTTP_X_ORDER_TOKEN="..."）"""
        headers = {"HTTP_X_CSRFTOKEN": self.csrf()} if csrf else {}
        return self.client.post(url, data or {}, format="json", **headers, **extra)
    
    def patch_json(self, url, data=None, csrf=True):
        headers = {"HTTP_X_CSRFTOKEN": self.csrf()} if csrf else {}
        return self.client.patch(url, data or {}, format="json", **headers)

    def put_json(self, url, data=None, csrf=True):
        headers = {"HTTP_X_CSRFTOKEN": self.csrf()} if csrf else {}
        return self.client.put(url, data or {}, format="json", **headers)

    def post_multipart(self, url, data, csrf=True):
        headers = {"HTTP_X_CSRFTOKEN": self.csrf()} if csrf else {}
        return self.client.post(url, data, format="multipart", **headers)

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
        genre=kw.pop("genre", Producer.Genre.AGRICULTURE),
        prefecture=kw.pop("prefecture", None) or make_prefecture(),
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
    category = kw.pop("category", None) or Category.objects.get_or_create(name="野菜", defaults={"sort_order": 1})[0]
    fields = dict(volume="1kg", description="説明", price=1000, publish_status=PublishStatus.PUBLIC)
    fields.update(kw)
    shipping_setting = fields.pop("shipping_setting", None) or producer.shipping_settings.first()
    return Product.objects.create(producer=producer, category=category, shipping_setting=shipping_setting,
                                  name=name, **fields)



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


def make_order(user=None, guest_email=None, payment_status=Order.PaymentStatus.PAID, payment_method="card", **kw):
    """注文だけを作る（箱と明細は add_shipment で足す）。user も guest_email もなければゲスト（guest@example.com）"""
    if user is None and guest_email is None:
        guest_email = "guest@example.com"
    number = Order.objects.count() + 1
    fields = dict(
        ship_name="佐藤 花子", ship_postal_code="1000001", ship_prefecture="東京都", ship_city="千代田区",
        ship_address_line1="千代田1-1", ship_phone="0312345678", items_total=0, shipping_total=0, grand_total=0,
        tax_8_amount=0, tax_10_amount=0, ordered_at=timezone.now(),
    )
    if guest_email:
        fields.update(guest_name="佐藤 花子", guest_phone="09012345678")
    fields.update(kw)
    return Order.objects.create(
        order_no=f"TM-20261106-{number:04d}", user=user, guest_email=guest_email,
        access_token_hash=f"{number:064x}", payment_status=payment_status, payment_method=payment_method, **fields)


def add_shipment(order, producer, items=((None, 1),), status=OrderShipment.Status.UNSHIPPED, temperature_zone="normal",
                 shipping_fee=1000, **kw):
    """注文に箱（生産者×温度帯）と明細を足す。items は (商品, 数量) の並び。商品が None なら producer の商品を作る

    明細の価格は商品の sale_price を写す。注文の合計金額も足し込む。
    """
    shipment = OrderShipment.objects.create(order=order, producer=producer, temperature_zone=temperature_zone,
                                            shipping_fee=shipping_fee, status=status, **kw)
    items_total = 0
    for product, quantity in items:
        product = product or make_product(producer)
        product.refresh_from_db()
        subtotal = product.sale_price * quantity
        OrderItem.objects.create(shipment=shipment, product=product, product_name=product.name,
                                 unit_price=product.price, discount_rate=product.discount_rate,
                                 paid_unit_price=product.sale_price, quantity=quantity, tax_rate=product.tax_rate,
                                 subtotal=subtotal)
        items_total += subtotal
    order.items_total += items_total
    order.shipping_total += shipping_fee
    order.grand_total += items_total + shipping_fee
    order.save(update_fields=["items_total", "shipping_total", "grand_total"])
    return shipment
