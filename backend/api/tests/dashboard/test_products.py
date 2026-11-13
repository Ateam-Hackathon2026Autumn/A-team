"""商品管理（生産者） のテスト

テスト対象: api/views/dashboard/products.py
  - 商品一覧・登録: GET・POST /api/v1/dashboard/products
  - 商品詳細・更新・削除: GET・PATCH・DELETE /api/v1/dashboard/products/:productId
  - 在庫更新: PATCH /api/v1/dashboard/products/:productId/stock
画像は POST /api/v1/uploads/images でアップロードしたキーを使う（保存先はテスト用の一時フォルダー）。
"""
from datetime import timedelta

from django.utils import timezone

from marche.models import (CartItem, Category, FavoriteProduct, Producer, Product, ProductImage, PublishStatus,
                           ShippingSetting)

from ..public.test_uploads import image_file
from ..utils import ApiTestCase, add_shipment, make_order, make_producer, make_product, make_user

LIST_URL = "/api/v1/dashboard/products"


def detail_url(product_id):
    return f"/api/v1/dashboard/products/{product_id}"


def stock_url(product_id):
    return f"/api/v1/dashboard/products/{product_id}/stock"


class DashboardProductTestCase(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.producer = make_producer(business_name="山田農園")
        self.category = Category.objects.create(name="野菜", sort_order=1)
        self.shipping = self.producer.shipping_settings.get()
        self.signin(self.producer.user.email)

    def upload(self):
        return self.post_multipart("/api/v1/uploads/images", {"image": image_file()}).json()["key"]

    def body(self, **overrides):
        data = {"name": "にんじん", "volume": "1kg", "categoryId": self.category.id,
                "shippingSettingId": self.shipping.id, "price": 1000, "description": "甘いにんじんです"}
        data.update(overrides)
        return data


# =========================================================
# 登録
# =========================================================

class CreateTests(DashboardProductTestCase):
    def test_create_draft_with_defaults(self):
        res = self.post_json(LIST_URL, self.body(name="  にんじん  "))
        self.assertEqual(res.status_code, 201)
        body = res.json()
        self.assertEqual(res["Location"], f"/api/v1/dashboard/products/{body['id']}")
        self.assertEqual(set(body), {
            "id", "producerId", "name", "volume", "categoryId", "shippingSettingId", "price", "taxRate",
            "discountRate", "description", "method", "isSubscription", "isPreorder", "acceptsDeliveryDate",
            "publishStatus", "salePrice", "stock", "ratingAvg", "reviewCount", "images", "createdAt", "updatedAt"})
        self.assertEqual((body["name"], body["taxRate"], body["publishStatus"], body["stock"], body["images"],
                          body["salePrice"], body["method"], body["reviewCount"], body["ratingAvg"]),
                         ("にんじん", 8, "draft", None, [], 1000, None, 0, None))

    def test_create_public_with_images(self):
        first, second = self.upload(), self.upload()
        res = self.post_json(LIST_URL, self.body(publishStatus="public", imageKeys=[first, second], discountRate=15,
                                                 stock=5, taxRate=10, method="無農薬", isSubscription=True))
        self.assertEqual(res.status_code, 201)
        body = res.json()
        self.assertEqual([(image["key"], image["sortOrder"]) for image in body["images"]], [(first, 0), (second, 1)])
        self.assertEqual((body["salePrice"], body["stock"], body["taxRate"], body["publishStatus"]),
                         (850, 5, 10, "public"))
        self.assertEqual(body["images"][0]["url"], f"/media/{first}")

    def test_public_needs_image_and_positive_sale_price(self):
        res = self.post_json(LIST_URL, self.body(publishStatus="public"))
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()["details"]["publishStatus"], ["公開するには画像を1枚以上登録してください。"])
        res = self.post_json(LIST_URL, self.body(publishStatus="public", price=1, discountRate=50,
                                                 imageKeys=[self.upload()]))
        self.assertEqual(res.json()["details"]["publishStatus"], ["公開するには割引後の価格を1円以上にしてください。"])
        self.assertEqual(Product.objects.count(), 0)

    def test_invalid_references_are_400(self):
        other = make_producer()
        others_shipping = other.shipping_settings.get()
        others_image = f"images/{other.user_id}/x.jpg"
        cases = [
            (self.body(categoryId=999), "categoryId"),
            (self.body(shippingSettingId=others_shipping.id), "shippingSettingId"),
            (self.body(imageKeys=[others_image]), "imageKeys"),
            (self.body(imageKeys=[f"images/{self.producer.user_id}/missing.jpg"]), "imageKeys"),
        ]
        for data, field in cases:
            with self.subTest(field=field):
                res = self.post_json(LIST_URL, data)
                self.assertEqual(res.status_code, 400)
                self.assertIn(field, res.json()["details"])

    def test_invalid_body_is_400(self):
        key = self.upload()
        bad = [
            {**self.body(), "name": "   "}, {**self.body(), "price": 0}, {**self.body(), "taxRate": 5},
            {**self.body(), "discountRate": 100}, {**self.body(), "publishStatus": "suspended"},
            {**self.body(), "imageKeys": [key, key]}, {**self.body(), "imageKeys": [key] * 11},
            {**self.body(), "salePrice": 1}, {**self.body(), "description": ""},
            {k: v for k, v in self.body().items() if k != "description"},
        ]
        for data in bad:
            with self.subTest(data=data):
                self.assertEqual(self.post_json(LIST_URL, data).status_code, 400)

    def test_suspended_producer_is_409(self):
        self.producer.publish_status = PublishStatus.SUSPENDED
        self.producer.save()
        res = self.post_json(LIST_URL, self.body())
        self.assertEqual((res.status_code, res.json()["errorCode"]), (409, "PRODUCER_SUSPENDED"))

    def test_not_approved_is_403(self):
        pending = make_producer(approval=Producer.ApprovalStatus.PENDING)
        self.post_json("/api/v1/auth/signout")
        self.signin(pending.user.email)
        self.assertEqual(self.client.get(LIST_URL).status_code, 403)


# =========================================================
# 一覧・詳細
# =========================================================

class ListDetailTests(DashboardProductTestCase):
    def test_only_mine_with_filters_and_order(self):
        fruit = Category.objects.create(name="果物", sort_order=2)
        old = make_product(self.producer, name="古い", publish_status=PublishStatus.PRIVATE)
        new = make_product(self.producer, name="新しい", category=fruit)
        Product.objects.filter(pk=old.pk).update(updated_at=timezone.now() - timedelta(days=1))
        make_product(make_producer(), name="他人の商品")

        self.assertEqual([item["id"] for item in self.client.get(LIST_URL).json()["items"]], [new.id, old.id])
        self.assertEqual([item["id"] for item in self.client.get(LIST_URL, {"publishStatus": "private"})
                          .json()["items"]], [old.id])
        self.assertEqual([item["id"] for item in self.client.get(LIST_URL, {"categoryId": fruit.id})
                          .json()["items"]], [new.id])
        for query in ["?publishStatus=hidden", "?categoryId=abc", "?foo=1"]:
            self.assertEqual(self.client.get(LIST_URL + query).status_code, 400)

    def test_query_count(self):
        for i in range(5):
            product = make_product(self.producer, name=f"商品{i}")
            ProductImage.objects.create(product=product, image=f"images/1/{i}.jpg", sort_order=0)
        with self.assertNumQueries(8):  # セッション・ユーザー・生産者・件数・商品・画像＋SAVEPOINT・RELEASE
            self.client.get(LIST_URL)

    def test_detail_and_404(self):
        mine = make_product(self.producer)
        others = make_product(make_producer())
        self.assertEqual(self.client.get(detail_url(mine.id)).json()["id"], mine.id)
        for product_id in [others.id, 999999]:
            res = self.client.get(detail_url(product_id))
            self.assertEqual((res.status_code, res.json()["errorCode"]), (404, "NOT_FOUND"))


# =========================================================
# 更新
# =========================================================

class UpdateTests(DashboardProductTestCase):
    def setUp(self):
        super().setUp()
        self.product = make_product(self.producer, stock=3, publish_status=PublishStatus.DRAFT)

    def test_partial_update_keeps_other_fields(self):
        res = self.patch_json(detail_url(self.product.id), {"price": 2000, "discountRate": 10, "method": ""})
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual((body["price"], body["salePrice"], body["name"], body["stock"], body["method"]),
                         (2000, 1800, "にんじん", 3, None))
        res = self.patch_json(detail_url(self.product.id), {"discountRate": None})
        self.assertEqual(res.json()["salePrice"], 2000)

    def test_replace_images_and_publish(self):
        ProductImage.objects.create(product=self.product, image="images/old.jpg", sort_order=0)
        key = self.upload()
        res = self.patch_json(detail_url(self.product.id), {"imageKeys": [key], "publishStatus": "public"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual([image["key"] for image in res.json()["images"]], [key])
        # 公開中に画像を全部外すことはできない
        res = self.patch_json(detail_url(self.product.id), {"imageKeys": []})
        self.assertEqual(res.status_code, 400)
        self.assertIn("publishStatus", res.json()["details"])
        self.assertEqual(self.product.product_images.count(), 1)

    def test_publish_without_image_is_400(self):
        res = self.patch_json(detail_url(self.product.id), {"publishStatus": "public"})
        self.assertEqual(res.status_code, 400)

    def test_invalid_patch_is_400(self):
        for data in [{}, {"stock": 5}, {"foo": 1}, {"name": ""}, {"publishStatus": "suspended"}]:
            with self.subTest(data=data):
                self.assertEqual(self.patch_json(detail_url(self.product.id), data).status_code, 400)

    def test_suspended_product_can_edit_but_not_change_status(self):
        Product.objects.filter(pk=self.product.pk).update(publish_status=PublishStatus.SUSPENDED)
        self.assertEqual(self.patch_json(detail_url(self.product.id), {"name": "直しました"}).status_code, 200)
        res = self.patch_json(detail_url(self.product.id), {"publishStatus": "private"})
        self.assertEqual((res.status_code, res.json()["errorCode"]), (409, "CONTENT_SUSPENDED"))

    def test_others_product_is_404(self):
        others = make_product(make_producer())
        self.assertEqual(self.patch_json(detail_url(others.id), {"name": "x"}).status_code, 404)


# =========================================================
# 削除・在庫更新
# =========================================================

class DeleteStockTests(DashboardProductTestCase):
    def test_delete_private_product_with_related_rows(self):
        product = make_product(self.producer, publish_status=PublishStatus.PRIVATE)
        ProductImage.objects.create(product=product, image="images/x.jpg", sort_order=0)
        buyer = make_user(email="buyer@example.com")
        FavoriteProduct.objects.create(user=buyer, product=product)
        CartItem.objects.create(user=buyer, product=product, quantity=1)
        res = self.delete_json(detail_url(product.id))
        self.assertEqual(res.status_code, 204)
        self.assertFalse(Product.objects.filter(pk=product.pk).exists())
        self.assertEqual((ProductImage.objects.count(), FavoriteProduct.objects.count(), CartItem.objects.count()),
                         (0, 0, 0))
        self.assertEqual(self.delete_json(detail_url(product.id)).status_code, 404)

    def test_delete_conflicts(self):
        public = make_product(self.producer)
        suspended = make_product(self.producer, publish_status=PublishStatus.SUSPENDED)
        ordered = make_product(self.producer, publish_status=PublishStatus.PRIVATE)
        add_shipment(make_order(user=make_user(email="buyer@example.com")), self.producer, items=((ordered, 1),))
        for product in [public, suspended, ordered]:
            with self.subTest(status=product.publish_status):
                res = self.delete_json(detail_url(product.id))
                self.assertEqual((res.status_code, res.json()["errorCode"]), (409, "PRODUCT_DELETE_CONFLICT"))

    def test_update_stock(self):
        product = make_product(self.producer, stock=3)
        res = self.patch_json(stock_url(product.id), {"stock": 10})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(set(res.json()), {"productId", "stock", "updatedAt"})
        self.assertEqual(res.json()["stock"], 10)
        # 公開中でも null（在庫管理しない）にできる
        self.assertEqual(self.patch_json(stock_url(product.id), {"stock": None}).json()["stock"], None)
        for data in [{}, {"stock": -1}, {"stock": 1, "price": 1}]:
            with self.subTest(data=data):
                self.assertEqual(self.patch_json(stock_url(product.id), data).status_code, 400)
        others = make_product(make_producer())
        self.assertEqual(self.patch_json(stock_url(others.id), {"stock": 1}).status_code, 404)


class ShippingSettingsTests(ApiTestCase):
    URL = "/api/v1/dashboard/shipping-settings"

    def setUp(self):
        super().setUp()
        self.producer = make_producer()
        self.normal = self.producer.shipping_settings.get()
        self.signin(self.producer.user.email)

    def item(self, zone, fee=800, threshold=None, lead="2〜4日で発送"):
        return {"temperatureZone": zone, "shippingFee": fee, "freeShippingThreshold": threshold,
                "leadTimeText": lead}

    def test_get(self):
        ShippingSetting.objects.create(producer=self.producer, temperature_zone="frozen", shipping_fee=1500,
                                       lead_time_text="翌日発送")
        res = self.client.get(self.URL)
        self.assertEqual(res.status_code, 200)
        self.assertEqual([item["temperatureZone"] for item in res.json()["items"]], ["normal", "frozen"])
        self.assertEqual(set(res.json()["items"][0]),
                         {"id", "temperatureZone", "shippingFee", "freeShippingThreshold", "leadTimeText"})

    def test_put_updates_in_place_and_adds(self):
        res = self.put_json(self.URL, {"items": [self.item("normal", 700, 5000), self.item("chilled", 1200)]})
        self.assertEqual(res.status_code, 200)
        items = res.json()["items"]
        self.assertEqual([(item["temperatureZone"], item["shippingFee"]) for item in items],
                         [("normal", 700), ("chilled", 1200)])
        self.assertEqual(items[0]["id"], self.normal.id)  # 同じ温度帯は id が変わらない
        self.assertEqual(items[0]["freeShippingThreshold"], 5000)

    def test_removing_used_zone_is_409(self):
        make_product(self.producer)  # 常温の配送設定を使う
        res = self.put_json(self.URL, {"items": [self.item("frozen")]})
        self.assertEqual((res.status_code, res.json()["errorCode"]), (409, "SHIPPING_SETTING_IN_USE"))
        self.assertEqual(list(ShippingSetting.objects.filter(producer=self.producer).values_list(
            "temperature_zone", flat=True)), ["normal"])

    def test_removing_unused_zone(self):
        res = self.put_json(self.URL, {"items": [self.item("frozen")]})
        self.assertEqual([item["temperatureZone"] for item in res.json()["items"]], ["frozen"])

    def test_invalid_body_is_400(self):
        bad = [{}, {"items": [self.item("normal"), self.item("normal")]}, {"items": [self.item("hot")]},
               {"items": [self.item("normal", -1)]}, {"items": [{**self.item("normal"), "id": 1}]},
               {"items": [self.item("normal", lead="")]}]
        for data in bad:
            with self.subTest(data=data):
                self.assertEqual(self.put_json(self.URL, data).status_code, 400)

    def test_suspended_producer_can_still_save(self):
        self.producer.publish_status = PublishStatus.SUSPENDED
        self.producer.save()
        self.assertEqual(self.put_json(self.URL, {"items": [self.item("normal")]}).status_code, 200)
