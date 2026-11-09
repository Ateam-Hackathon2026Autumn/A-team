"""お気に入り のテスト

テスト対象: api/views/public/favorites.py
  - お気に入り一覧: GET /api/v1/users/me/favorites
  - 商品の登録・解除: PUT・DELETE /api/v1/users/me/favorites/products/:productId
  - 生産者の登録・解除: PUT・DELETE /api/v1/users/me/favorites/producers/:producerId
"""
from datetime import timedelta

from django.utils import timezone

from marche.models import FavoriteProducer, FavoriteProduct, ProductImage, PublishStatus

from ..utils import ApiTestCase, make_producer, make_product, make_user

LIST_URL = "/api/v1/users/me/favorites"


def product_url(product_id):
    return f"/api/v1/users/me/favorites/products/{product_id}"


def producer_url(producer_id):
    return f"/api/v1/users/me/favorites/producers/{producer_id}"


class FavoriteTestCase(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.producer = make_producer(business_name="山田農園")
        self.product = make_product(self.producer)
        self.user = make_user(email="buyer@example.com")
        self.signin(self.user.email)


# =========================================================
# 商品の登録・解除
# =========================================================

class ProductFavoriteTests(FavoriteTestCase):
    def test_put_and_delete_are_idempotent(self):
        for _ in range(2):
            res = self.put_json(product_url(self.product.id))
            self.assertEqual((res.status_code, res.content), (204, b""))
        self.assertEqual(FavoriteProduct.objects.filter(user=self.user).count(), 1)
        # 商品詳細のお気に入り済みにも反映される
        self.assertTrue(self.client.get(f"/api/v1/products/{self.product.id}").json()["isFavorited"])
        for _ in range(2):
            self.assertEqual(self.delete_json(product_url(self.product.id)).status_code, 204)
        self.assertFalse(FavoriteProduct.objects.exists())
        self.assertEqual(self.delete_json(product_url(999999)).status_code, 204)

    def test_only_public_products(self):
        hidden = make_product(self.producer, publish_status=PublishStatus.PRIVATE)
        for product_id in [hidden.id, 999999, 2 ** 63]:
            res = self.put_json(product_url(product_id))
            self.assertEqual((res.status_code, res.json()["errorCode"]), (404, "PRODUCT_NOT_FOUND"))

    def test_can_remove_after_it_became_private(self):
        FavoriteProduct.objects.create(user=self.user, product=self.product)
        self.product.publish_status = PublishStatus.PRIVATE
        self.product.save()
        self.assertEqual(self.delete_json(product_url(self.product.id)).status_code, 204)
        self.assertFalse(FavoriteProduct.objects.exists())

    def test_own_product_is_409(self):
        self.post_json("/api/v1/auth/signout")
        self.signin(self.producer.user.email)
        res = self.put_json(product_url(self.product.id))
        self.assertEqual((res.status_code, res.json()["errorCode"]), (409, "CANNOT_FAVORITE_OWN"))

    def test_body_login_and_csrf(self):
        self.assertEqual(self.put_json(product_url(self.product.id), {"notify": True}).status_code, 400)
        res = self.put_json(product_url(self.product.id), csrf=False)
        self.assertEqual((res.status_code, res.json()["errorCode"]), (403, "CSRF_FAILED"))
        self.post_json("/api/v1/auth/signout")
        self.assertEqual(self.put_json(product_url(self.product.id)).status_code, 401)


# =========================================================
# 生産者の登録・解除
# =========================================================

class ProducerFavoriteTests(FavoriteTestCase):
    def favorite(self):
        return FavoriteProducer.objects.get(user=self.user, producer=self.producer)

    def test_notify_defaults_to_false_and_is_kept_when_omitted(self):
        self.assertEqual(self.put_json(producer_url(self.producer.id)).status_code, 204)
        self.assertFalse(self.favorite().notify)
        self.put_json(producer_url(self.producer.id), {"notify": True})
        self.assertTrue(self.favorite().notify)
        self.put_json(producer_url(self.producer.id))  # 省略したら今の値のまま
        self.assertTrue(self.favorite().notify)
        self.put_json(producer_url(self.producer.id), {"notify": False})
        self.assertFalse(self.favorite().notify)
        self.assertEqual(FavoriteProducer.objects.count(), 1)

    def test_new_with_notify(self):
        self.put_json(producer_url(self.producer.id), {"notify": True})
        self.assertTrue(self.favorite().notify)

    def test_errors(self):
        hidden = make_producer(publish=PublishStatus.PRIVATE)
        res = self.put_json(producer_url(hidden.id))
        self.assertEqual((res.status_code, res.json()["errorCode"]), (404, "PRODUCER_NOT_FOUND"))
        self.assertEqual(self.put_json(producer_url(self.producer.id), {"foo": 1}).status_code, 400)
        self.assertEqual(self.put_json(producer_url(self.producer.id), {"notify": "maybe"}).status_code, 400)
        self.post_json("/api/v1/auth/signout")
        self.signin(self.producer.user.email)
        res = self.put_json(producer_url(self.producer.id))
        self.assertEqual((res.status_code, res.json()["errorCode"]), (409, "CANNOT_FAVORITE_OWN"))

    def test_delete(self):
        FavoriteProducer.objects.create(user=self.user, producer=self.producer)
        self.producer.publish_status = PublishStatus.SUSPENDED
        self.producer.save()
        self.assertEqual(self.delete_json(producer_url(self.producer.id)).status_code, 204)
        self.assertFalse(FavoriteProducer.objects.exists())


# =========================================================
# 一覧
# =========================================================

class FavoriteListTests(FavoriteTestCase):
    def test_products(self):
        older = make_product(self.producer, name="古い")
        ProductImage.objects.create(product=self.product, image="images/1/a.jpg", sort_order=0)
        FavoriteProduct.objects.create(user=self.user, product=older)
        FavoriteProduct.objects.create(user=self.user, product=self.product)
        FavoriteProduct.objects.filter(product=older).update(created_at=timezone.now() - timedelta(days=1))
        older.publish_status = PublishStatus.PRIVATE
        older.save()
        FavoriteProduct.objects.create(user=make_user(email="other@example.com"), product=self.product)

        res = self.client.get(LIST_URL, {"type": "product"})
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual((body["total"], body["page"], body["pageSize"], body["totalPages"]), (2, 1, 20, 1))
        first, second = body["items"]
        self.assertEqual(set(first), {"product", "isPublic", "favoritedAt"})
        self.assertEqual((first["product"]["id"], first["isPublic"]), (self.product.id, True))
        self.assertEqual((first["product"]["thumbnailUrl"], first["product"]["isFavorited"]),
                         ("/media/images/1/a.jpg", True))
        self.assertEqual(first["product"]["producer"]["businessName"], "山田農園")
        self.assertEqual((second["product"]["id"], second["isPublic"]), (older.id, False))

    def test_producers(self):
        hidden = make_producer(business_name="休業中の農園")
        FavoriteProducer.objects.create(user=self.user, producer=hidden, notify=True)
        FavoriteProducer.objects.create(user=self.user, producer=self.producer)
        FavoriteProducer.objects.filter(producer=hidden).update(created_at=timezone.now() - timedelta(days=1))
        hidden.user.is_active = False
        hidden.user.save()

        items = self.client.get(LIST_URL, {"type": "producer"}).json()["items"]
        self.assertEqual(set(items[0]), {"producer", "isPublic", "notify", "favoritedAt"})
        self.assertEqual([(item["producer"]["id"], item["isPublic"], item["notify"]) for item in items],
                         [(self.producer.id, True, False), (hidden.id, False, True)])
        self.assertTrue(items[0]["producer"]["isFavorited"])
        self.assertIn("badges", items[0]["producer"])

    def test_invalid_query_and_login(self):
        for query in ["", "?type=story", "?type=product&foo=1"]:
            with self.subTest(query=query):
                self.assertEqual(self.client.get(LIST_URL + query).status_code, 400)
        self.post_json("/api/v1/auth/signout")
        self.assertEqual(self.client.get(LIST_URL, {"type": "product"}).status_code, 401)

    def test_query_count(self):
        for i in range(5):
            product = make_product(make_producer(), name=f"商品{i}")
            FavoriteProduct.objects.create(user=self.user, product=product)
            FavoriteProducer.objects.create(user=self.user, producer=product.producer)
        for favorite_type in ["product", "producer"]:
            with self.subTest(type=favorite_type), self.assertNumQueries(6):
                # セッション・ユーザー・件数・一覧（JOIN とサブクエリ）＋SAVEPOINT・RELEASE
                self.client.get(LIST_URL, {"type": favorite_type})
