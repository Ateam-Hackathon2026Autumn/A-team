"""カート のテスト

テスト対象: api/views/public/cart.py（services/cart.py・services/pricing.py の箱分け・送料）
  - カート取得: GET /api/v1/cart
  - カートに追加: POST /api/v1/cart/items
  - 数量変更・削除: PATCH・DELETE /api/v1/cart/items/:itemId
"""
from datetime import timedelta

from django.utils import timezone

from marche.models import CartItem, ProductImage, PublishStatus, ShippingSetting

from ..utils import ApiTestCase, make_producer, make_product, make_user

CART_URL = "/api/v1/cart"
ITEMS_URL = "/api/v1/cart/items"


def item_url(item_id):
    return f"/api/v1/cart/items/{item_id}"


class CartTestCase(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.producer = make_producer(business_name="山田農園")
        self.product = make_product(self.producer, price=1000, stock=5)

    def add(self, product, quantity=1, **kw):
        return self.post_json(ITEMS_URL, {"productId": product.id, "quantity": quantity}, **kw)

    def error_code(self, res):
        return res.status_code, res.json()["errorCode"]


# =========================================================
# ゲスト
# =========================================================

class GuestCartTests(CartTestCase):
    def test_get_without_session_is_empty_and_creates_no_session(self):
        res = self.client.get(CART_URL)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {"items": [], "shipments": [], "itemsTotal": 0, "shippingTotal": 0,
                                      "total": 0, "canCheckout": False})
        self.assertNotIn("sessionid", res.cookies)

    def test_add_creates_session_and_merges_on_signin(self):
        res = self.add(self.product, 2)
        self.assertEqual(res.status_code, 200)
        self.assertIn("sessionid", res.cookies)
        self.assertEqual(res.json()["items"][0]["quantity"], 2)
        self.assertEqual(self.client.get(CART_URL).json()["items"][0]["quantity"], 2)
        item = CartItem.objects.get()
        self.assertIsNone(item.user_id)

        user = make_user(email="buyer@example.com")
        self.signin(user.email)
        item.refresh_from_db()
        self.assertEqual((item.user_id, item.session_key), (user.id, None))
        self.assertEqual(self.client.get(CART_URL).json()["items"][0]["id"], item.id)

    def test_patch_delete_without_session_is_404(self):
        for res in [self.patch_json(item_url(1), {"quantity": 1}), self.delete_json(item_url(1))]:
            self.assertEqual(self.error_code(res), (404, "CART_ITEM_NOT_FOUND"))

    def test_csrf(self):
        self.assertEqual(self.error_code(self.add(self.product, csrf=False)), (403, "CSRF_FAILED"))
        self.assertFalse(CartItem.objects.exists())


# =========================================================
# 中身の組み立て（明細・箱・送料・購入できない理由）
# =========================================================

class CartContentTests(CartTestCase):
    def setUp(self):
        super().setUp()
        self.user = make_user(email="buyer@example.com")
        self.signin(self.user.email)

    def put(self, product, quantity=1, minutes_ago=0):
        item = CartItem.objects.create(user=self.user, product=product, quantity=quantity)
        CartItem.objects.filter(pk=item.pk).update(created_at=timezone.now() - timedelta(minutes=minutes_ago))
        return item

    def test_lines_and_boxes(self):
        ProductImage.objects.create(product=self.product, image="images/1/a.jpg", sort_order=0)
        chilled = ShippingSetting.objects.create(producer=self.producer, temperature_zone="chilled",
                                                 shipping_fee=1500, free_shipping_threshold=3000,
                                                 lead_time_text="翌日発送")
        milk = make_product(self.producer, name="牛乳", price=1500)
        milk.shipping_setting = chilled
        milk.save()
        other = make_producer(business_name="海の幸")
        fish = make_product(other, name="さば", price=800)
        first = self.put(self.product, 2, minutes_ago=3)
        second = self.put(milk, 2, minutes_ago=2)
        third = self.put(fish, 1, minutes_ago=1)

        body = self.client.get(CART_URL).json()
        self.assertEqual([line["id"] for line in body["items"]], [first.id, second.id, third.id])
        line = body["items"][0]
        self.assertEqual(line, {"id": first.id, "productId": self.product.id, "productName": "にんじん",
                                "volume": "1kg", "thumbnailUrl": "/media/images/1/a.jpg", "quantity": 2,
                                "unitPrice": 1000, "subtotal": 2000, "purchasable": True,
                                "unavailableReason": None})
        self.assertEqual(body["shipments"], [
            {"producerId": self.producer.id, "producerName": "山田農園", "temperatureZone": "normal",
             "itemIds": [first.id], "itemsTotal": 2000, "shippingFee": 1000, "freeShippingThreshold": None},
            {"producerId": self.producer.id, "producerName": "山田農園", "temperatureZone": "chilled",
             "itemIds": [second.id], "itemsTotal": 3000, "shippingFee": 0, "freeShippingThreshold": 3000},
            {"producerId": other.id, "producerName": "海の幸", "temperatureZone": "normal",
             "itemIds": [third.id], "itemsTotal": 800, "shippingFee": 1000, "freeShippingThreshold": None},
        ])
        self.assertEqual((body["itemsTotal"], body["shippingTotal"], body["total"], body["canCheckout"]),
                         (5800, 2000, 7800, True))

    def test_same_box_items_are_summed(self):
        carrot = self.put(self.product, 1, minutes_ago=2)
        onion = self.put(make_product(self.producer, name="たまねぎ", price=500), 2, minutes_ago=1)
        shipments = self.client.get(CART_URL).json()["shipments"]
        self.assertEqual(len(shipments), 1)
        self.assertEqual((shipments[0]["itemIds"], shipments[0]["itemsTotal"]), ([carrot.id, onion.id], 2000))

    def test_unavailable_reasons(self):
        hidden = make_product(self.producer, name="非公開", publish_status=PublishStatus.PRIVATE)
        subscription = make_product(self.producer, name="定期便", is_subscription=True)
        sold_out = make_product(self.producer, name="売り切れ", stock=0)
        few = make_product(self.producer, name="残りわずか", stock=1)
        unmanaged = make_product(self.producer, name="在庫管理なし", stock=None)
        for i, product in enumerate([hidden, subscription, sold_out, few, unmanaged]):
            self.put(product, 2, minutes_ago=10 - i)

        body = self.client.get(CART_URL).json()
        self.assertEqual([(line["purchasable"], line["unavailableReason"]) for line in body["items"]], [
            (False, "PRODUCT_UNAVAILABLE"), (False, "UNSUPPORTED_PRODUCT"), (False, "OUT_OF_STOCK"),
            (False, "QUANTITY_EXCEEDS_STOCK"), (True, None)])
        hidden_line = body["items"][0]
        self.assertEqual((hidden_line["productName"], hidden_line["unitPrice"], hidden_line["subtotal"],
                          hidden_line["thumbnailUrl"]), (None, None, None, None))
        self.assertEqual(body["items"][1]["productName"], "定期便")
        # 購入できない明細は箱と合計に入れない
        self.assertEqual(body["shipments"][0]["itemIds"], [body["items"][4]["id"]])
        self.assertEqual((body["itemsTotal"], body["total"], body["canCheckout"]), (2000, 3000, False))

    def test_suspended_producer_is_unavailable(self):
        self.put(self.product)
        self.producer.publish_status = PublishStatus.SUSPENDED
        self.producer.save()
        line = self.client.get(CART_URL).json()["items"][0]
        self.assertEqual(line["unavailableReason"], "PRODUCT_UNAVAILABLE")

    def test_price_is_always_latest(self):
        self.put(self.product, 2)
        self.product.price = 1200
        self.product.save()
        self.assertEqual(self.client.get(CART_URL).json()["itemsTotal"], 2400)

    def test_other_users_cart_is_not_shown(self):
        CartItem.objects.create(user=make_user(email="other@example.com"), product=self.product, quantity=1)
        self.assertEqual(self.client.get(CART_URL).json()["items"], [])

    def test_query_params_are_rejected(self):
        self.assertEqual(self.client.get(CART_URL, {"foo": 1}).status_code, 400)

    def test_query_count(self):
        for i in range(5):
            product = make_product(make_producer(), name=f"商品{i}")
            ProductImage.objects.create(product=product, image=f"images/1/{i}.jpg", sort_order=0)
            self.put(product)
        with self.assertNumQueries(3):  # セッション・ユーザー・明細（JOIN とサブクエリ）
            self.client.get(CART_URL)


# =========================================================
# 追加
# =========================================================

class CartAddTests(CartTestCase):
    def setUp(self):
        super().setUp()
        self.user = make_user(email="buyer@example.com")
        self.signin(self.user.email)

    def test_add_twice_sums_quantity(self):
        self.assertEqual(self.add(self.product, 2).status_code, 200)
        res = self.add(self.product, 3)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["items"][0]["quantity"], 5)
        item = CartItem.objects.get()
        self.assertEqual((item.user_id, item.session_key, item.quantity), (self.user.id, None, 5))

    def test_over_ten_is_400(self):
        unmanaged = make_product(self.producer, name="在庫管理なし", stock=None)
        self.add(unmanaged, 8)
        res = self.add(unmanaged, 3)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(CartItem.objects.get().quantity, 8)
        for body in [{"productId": unmanaged.id, "quantity": 11}, {"productId": unmanaged.id, "quantity": 0},
                     {"productId": unmanaged.id}, {"productId": unmanaged.id, "quantity": 1, "foo": 1},
                     {"productId": "abc", "quantity": 1}]:
            with self.subTest(body=body):
                self.assertEqual(self.post_json(ITEMS_URL, body).status_code, 400)

    def test_product_must_be_public(self):
        hidden = make_product(self.producer, publish_status=PublishStatus.PRIVATE)
        for product_id in [hidden.id, 999999, 2 ** 63 - 1]:
            res = self.post_json(ITEMS_URL, {"productId": product_id, "quantity": 1})
            self.assertEqual(self.error_code(res), (404, "PRODUCT_NOT_FOUND"))
        self.assertEqual(self.post_json(ITEMS_URL, {"productId": 2 ** 63, "quantity": 1}).status_code, 400)

    def test_conflicts(self):
        subscription = make_product(self.producer, name="定期便", is_subscription=True)
        sold_out = make_product(self.producer, name="売り切れ", stock=0)
        self.assertEqual(self.error_code(self.add(subscription)), (409, "UNSUPPORTED_PRODUCT"))
        self.assertEqual(self.error_code(self.add(sold_out)), (409, "OUT_OF_STOCK"))
        self.add(self.product, 4)
        self.assertEqual(self.error_code(self.add(self.product, 2)), (409, "QUANTITY_EXCEEDS_STOCK"))
        self.assertEqual(CartItem.objects.get().quantity, 4)  # 失敗したら変えない

    def test_own_product_is_409(self):
        self.post_json("/api/v1/auth/signout")
        self.signin(self.producer.user.email)
        self.assertEqual(self.error_code(self.add(self.product)), (409, "CANNOT_PURCHASE_OWN"))

    def test_up_to_fifty_kinds(self):
        products = [make_product(self.producer, name=f"商品{i}") for i in range(51)]
        CartItem.objects.bulk_create(CartItem(user=self.user, product=p, quantity=1) for p in products[:50])
        self.assertEqual(self.error_code(self.add(products[50])), (409, "CART_LIMIT_EXCEEDED"))
        self.assertEqual(self.add(products[0]).status_code, 200)  # 入っている商品の追加はできる

    def test_does_not_reduce_stock(self):
        self.add(self.product, 3)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)


# =========================================================
# 数量変更・削除
# =========================================================

class CartItemUpdateTests(CartTestCase):
    def setUp(self):
        super().setUp()
        self.user = make_user(email="buyer@example.com")
        self.signin(self.user.email)
        self.item = CartItem.objects.create(user=self.user, product=self.product, quantity=2)

    def test_patch_sets_quantity(self):
        res = self.patch_json(item_url(self.item.id), {"quantity": 4})
        self.assertEqual(res.status_code, 200)
        self.assertEqual((res.json()["items"][0]["quantity"], res.json()["itemsTotal"]), (4, 4000))

    def test_patch_errors(self):
        for body in [{"quantity": 0}, {"quantity": 11}, {}, {"quantity": 1, "productId": 1}]:
            with self.subTest(body=body):
                self.assertEqual(self.patch_json(item_url(self.item.id), body).status_code, 400)
        res = self.patch_json(item_url(self.item.id), {"quantity": 6})
        self.assertEqual(self.error_code(res), (409, "QUANTITY_EXCEEDS_STOCK"))
        self.item.refresh_from_db()
        self.assertEqual(self.item.quantity, 2)

        self.product.publish_status = PublishStatus.PRIVATE
        self.product.save()
        res = self.patch_json(item_url(self.item.id), {"quantity": 1})
        self.assertEqual(self.error_code(res), (409, "PRODUCT_UNAVAILABLE"))

    def test_other_users_item_is_404(self):
        other = CartItem.objects.create(user=make_user(email="other@example.com"), product=self.product, quantity=1)
        guest = CartItem.objects.create(session_key="x" * 32, product=self.product, quantity=1)
        for item_id in [other.id, guest.id, 999999, 2 ** 63]:
            with self.subTest(item_id=item_id):
                res = self.patch_json(item_url(item_id), {"quantity": 1})
                self.assertEqual(self.error_code(res), (404, "CART_ITEM_NOT_FOUND"))
                self.assertEqual(self.error_code(self.delete_json(item_url(item_id))), (404, "CART_ITEM_NOT_FOUND"))
        self.assertEqual(self.client.patch(item_url("abc")).status_code, 404)
        self.assertEqual(CartItem.objects.count(), 3)

    def test_delete_even_if_unavailable(self):
        self.product.publish_status = PublishStatus.PRIVATE
        self.product.save()
        res = self.delete_json(item_url(self.item.id))
        self.assertEqual((res.status_code, res.content), (204, b""))
        self.assertFalse(CartItem.objects.exists())
        self.assertEqual(self.error_code(self.delete_json(item_url(self.item.id))), (404, "CART_ITEM_NOT_FOUND"))

    def test_csrf(self):
        self.assertEqual(self.patch_json(item_url(self.item.id), {"quantity": 1}, csrf=False).status_code, 403)
        self.assertEqual(self.delete_json(item_url(self.item.id), csrf=False).status_code, 403)
        self.assertTrue(CartItem.objects.exists())
