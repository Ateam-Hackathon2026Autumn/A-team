"""商品・カテゴリー（公開側） のテスト

テスト対象: api/views/public/catalog.py
    - 商品一覧: GET /api/v1/products
    - 商品詳細: GET /api/v1/products/:productId
    - カテゴリー一覧: GET /api/v1/categories
商品レビュー一覧はステップ10（レビュー）でテストする。S3 には接続しない（ApiTestCase）。
"""
from datetime import timedelta

from django.utils import timezone

from marche.models import (Category, FavoriteProduct, Producer, ProducerStory, Product, ProductImage,
                            PublishStatus)

from ..utils import ApiTestCase, make_producer, make_product, make_user

LIST_URL = "/api/v1/products"
CATEGORY_URL = "/api/v1/categories"


def detail_url(product_id):
    return f"/api/v1/products/{product_id}"


def add_image(product, sort_order=0, name=None):
    return ProductImage.objects.create(product=product, sort_order=sort_order,
                                        image=name or f"images/1/p{product.id}-{sort_order}.jpg")


def ids(response):
    return [item["id"] for item in response.json()["items"]]


# =========================================================
# カテゴリー一覧
# =========================================================

class CategoryListTests(ApiTestCase):
    def test_sorted_by_sort_order_then_id(self):
        fruit = Category.objects.create(name="果物", sort_order=2)
        vegetable = Category.objects.create(name="野菜", sort_order=1)
        rice = Category.objects.create(name="米", sort_order=2)
        res = self.client.get(CATEGORY_URL)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {"items": [
            {"id": vegetable.id, "name": "野菜", "sortOrder": 1},
            {"id": fruit.id, "name": "果物", "sortOrder": 2},
            {"id": rice.id, "name": "米", "sortOrder": 2},
        ]})
        self.assertEqual(res["Cache-Control"], "no-store")

    def test_empty(self):
        self.assertEqual(self.client.get(CATEGORY_URL).json(), {"items": []})

    def test_unknown_query_is_400(self):
        res = self.client.get(CATEGORY_URL, {"page": 1})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()["errorCode"], "VALIDATION_ERROR")

    def test_fixture_loads(self):
        from django.core.management import call_command
        call_command("loaddata", "categories", verbosity=0)
        names = [item["name"] for item in self.client.get(CATEGORY_URL).json()["items"]]
        self.assertEqual(names, ["野菜", "果物", "米", "お茶", "魚介類", "肉", "加工品", "その他"])


# =========================================================
# 商品一覧
# =========================================================

class ProductListTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.producer = make_producer()

    def test_item_shape(self):
        product = make_product(self.producer, price=1000, discount_rate=15, stock=None, rating_avg="4.5",
                               review_count=2, is_subscription=True)
        add_image(product, sort_order=1, name="images/1/second.jpg")
        add_image(product, sort_order=0, name="images/1/main.jpg")
        res = self.client.get(LIST_URL)
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual((body["total"], body["page"], body["pageSize"], body["totalPages"]), (1, 1, 20, 1))
        self.assertEqual(body["items"][0], {
            "id": product.id, "name": "にんじん", "volume": "1kg", "price": 1000, "discountRate": 15,
            "salePrice": 850, "taxRate": 8, "ratingAvg": 4.5, "reviewCount": 2, "stock": None,
            "isSubscription": True, "isPreorder": False, "thumbnailUrl": "/media/images/1/main.jpg",
            "isFavorited": False,
            "category": {"id": product.category_id, "name": "野菜", "sortOrder": 1},
            "producer": {"id": self.producer.id, "businessName": "山田農園", "prefectureId": 13,
                            "prefectureName": "東京都", "city": "八王子市"},
        })

    def test_no_image_and_no_review(self):
        make_product(self.producer)
        item = self.client.get(LIST_URL).json()["items"][0]
        self.assertEqual((item["thumbnailUrl"], item["ratingAvg"], item["discountRate"]), (None, None, None))

    def test_sale_price_rounds_down(self):
        make_product(self.producer, price=999, discount_rate=33)  # 999 * 67 / 100 = 669.33
        self.assertEqual(self.client.get(LIST_URL).json()["items"][0]["salePrice"], 669)

    def test_sold_out_is_listed(self):
        make_product(self.producer, stock=0)
        self.assertEqual(self.client.get(LIST_URL).json()["items"][0]["stock"], 0)

    def test_only_public(self):
        visible = make_product(self.producer, name="公開")
        for status in [PublishStatus.DRAFT, PublishStatus.PRIVATE, PublishStatus.SUSPENDED]:
            make_product(self.producer, name=status, publish_status=status)
        make_product(make_producer(approval=Producer.ApprovalStatus.PENDING), name="審査待ち")
        make_product(make_producer(publish=PublishStatus.SUSPENDED), name="生産者が掲載停止")
        make_product(make_producer(publish=PublishStatus.PRIVATE), name="生産者が非公開")
        stopped = make_producer()
        stopped.user.is_active = False
        stopped.user.save()
        make_product(stopped, name="ユーザーが利用停止")
        withdrawn = make_producer()
        withdrawn.user.deleted_at = timezone.now()
        withdrawn.user.save()
        make_product(withdrawn, name="ユーザーが退会")
        res = self.client.get(LIST_URL)
        self.assertEqual(ids(res), [visible.id])
        self.assertEqual(res.json()["total"], 1)

    def test_filter_by_category_and_producer(self):
        fruit = Category.objects.create(name="果物", sort_order=2)
        other = make_producer()
        veg_mine = make_product(self.producer)
        fruit_mine = make_product(self.producer, category=fruit)
        fruit_other = make_product(other, category=fruit)
        self.assertEqual(ids(self.client.get(LIST_URL, {"categoryId": fruit.id})), [fruit_other.id, fruit_mine.id])
        self.assertEqual(ids(self.client.get(LIST_URL, {"producerId": self.producer.id})),
                            [fruit_mine.id, veg_mine.id])
        self.assertEqual(ids(self.client.get(LIST_URL, {"categoryId": fruit.id, "producerId": self.producer.id})),
                            [fruit_mine.id])

    def test_unknown_ids_return_empty(self):
        make_product(self.producer)
        hidden = make_producer(publish=PublishStatus.PRIVATE)
        for params in [{"categoryId": 999}, {"producerId": 999}, {"producerId": hidden.id}]:
            res = self.client.get(LIST_URL, params)
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json(), {"items": [], "total": 0, "page": 1, "pageSize": 20, "totalPages": 0})

    def test_invalid_query_is_400(self):
        bad = [
            "?unknown=1", "?sort=", "?sort=cheap", "?categoryId=", "?categoryId=abc", "?categoryId=0",
            "?producerId=-1", "?page=0", "?pageSize=101", "?sort=newest&sort=popular",
            f"?categoryId={2 ** 63}",
        ]
        for query in bad:
            with self.subTest(query=query):
                res = self.client.get(LIST_URL + query)
                self.assertEqual(res.status_code, 400)
                self.assertEqual(res.json()["errorCode"], "VALIDATION_ERROR")

    def test_paging(self):
        products = [make_product(self.producer, name=f"商品{i}") for i in range(5)]
        newest_first = [p.id for p in reversed(products)]
        res = self.client.get(LIST_URL, {"sort": "newest", "page": 2, "pageSize": 2})
        body = res.json()
        self.assertEqual((body["total"], body["page"], body["pageSize"], body["totalPages"]), (5, 2, 2, 3))
        self.assertEqual(ids(res), newest_first[2:4])
        out_of_range = self.client.get(LIST_URL, {"page": 4, "pageSize": 2}).json()
        self.assertEqual((out_of_range["items"], out_of_range["total"]), ([], 5))

    def test_sort_orders(self):
        now = timezone.now()
        a = make_product(self.producer, name="A", price=3000, popularity_score=10)
        b = make_product(self.producer, name="B", price=1000, popularity_score=30)
        c = make_product(self.producer, name="C", price=2000, popularity_score=10)
        d = make_product(self.producer, name="D", price=4000, discount_rate=90, popularity_score=20)  # 400円
        for i, product in enumerate([a, b, c, d]):
            Product.objects.filter(pk=product.pk).update(created_at=now - timedelta(days=10 - i))
        expected = {
            "popular": [b.id, d.id, c.id, a.id],   # 同じスコアは id の降順
            "newest": [d.id, c.id, b.id, a.id],
            "price_asc": [d.id, b.id, c.id, a.id],
            "price_desc": [a.id, c.id, b.id, d.id],
        }
        for sort, order in expected.items():
            with self.subTest(sort=sort):
                self.assertEqual(ids(self.client.get(LIST_URL, {"sort": sort})), order)
        self.assertEqual(ids(self.client.get(LIST_URL)), expected["popular"])  # 初期値は popular

    def test_rating_sort_puts_3_or_more_reviews_first(self):
        one_review = make_product(self.producer, name="1件で★5", rating_avg="5.0", review_count=1)
        many_low = make_product(self.producer, name="10件で★3", rating_avg="3.0", review_count=10)
        many_high = make_product(self.producer, name="3件で★4.5", rating_avg="4.5", review_count=3)
        no_review = make_product(self.producer, name="レビューなし")
        two_reviews = make_product(self.producer, name="2件で★4", rating_avg="4.0", review_count=2)
        self.assertEqual(ids(self.client.get(LIST_URL, {"sort": "rating"})),
                            [many_high.id, many_low.id, one_review.id, two_reviews.id, no_review.id])

    def test_is_favorited_when_signed_in(self):
        liked = make_product(self.producer, name="お気に入り")
        other = make_product(self.producer, name="その他")
        user = make_user(email="buyer@example.com")
        FavoriteProduct.objects.create(user=user, product=liked)
        FavoriteProduct.objects.create(user=make_user(email="someone@example.com"), product=other)
        self.signin("buyer@example.com")
        items = {item["id"]: item["isFavorited"] for item in self.client.get(LIST_URL).json()["items"]}
        self.assertEqual(items, {liked.id: True, other.id: False})

    def test_query_count(self):
        for i in range(3):
            product = make_product(make_producer(), name=f"商品{i}")
            add_image(product)
        with self.assertNumQueries(4):  # 件数・一覧（JOIN とサブクエリ）＋SAVEPOINT・RELEASE
            self.client.get(LIST_URL)
        user = make_user(email="buyer@example.com")
        self.signin(user.email)
        with self.assertNumQueries(6):  # セッション・ユーザー・件数・一覧＋SAVEPOINT・RELEASE
            self.client.get(LIST_URL, {"sort": "rating"})


# =========================================================
# 商品詳細
# =========================================================

class ProductDetailTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.producer = make_producer()
        self.product = make_product(self.producer, description="甘いにんじんです", method="無農薬で育てました",
                                    accepts_delivery_date=True, stock=5)

    def test_detail_shape(self):
        add_image(self.product, sort_order=1, name="images/1/b.jpg")
        first = add_image(self.product, sort_order=0, name="images/1/a.jpg")
        same_order = add_image(self.product, sort_order=1, name="images/1/c.jpg")
        ProducerStory.objects.create(producer=self.producer, craft="土づくりにこだわっています",
                                        publish_status=PublishStatus.PUBLIC)
        res = self.client.get(detail_url(self.product.id))
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["id"], self.product.id)
        self.assertEqual(body["thumbnailUrl"], "/media/images/1/a.jpg")
        self.assertEqual((body["description"], body["method"], body["acceptsDeliveryDate"], body["stock"]),
                            ("甘いにんじんです", "無農薬で育てました", True, 5))
        self.assertEqual([image["id"] for image in body["images"]][0], first.id)
        self.assertEqual([image["url"] for image in body["images"]],
                            ["/media/images/1/a.jpg", "/media/images/1/b.jpg", "/media/images/1/c.jpg"])
        self.assertEqual(body["images"][2], {"id": same_order.id, "url": "/media/images/1/c.jpg", "sortOrder": 1})
        self.assertEqual(body["shipping"], {"temperatureZone": "normal", "shippingFee": 1000,
                                            "freeShippingThreshold": None, "leadTimeText": "2〜4日で発送"})
        self.assertEqual(body["craft"], "土づくりにこだわっています")
        self.assertFalse(body["isFavorited"])
        self.assertEqual(set(body), {
            "id", "name", "volume", "price", "discountRate", "salePrice", "taxRate", "ratingAvg", "reviewCount",
            "stock", "isSubscription", "isPreorder", "thumbnailUrl", "isFavorited", "category", "producer",
            "description", "method", "acceptsDeliveryDate", "images", "shipping", "craft"})

    def test_no_images_and_empty_method(self):
        Product.objects.filter(pk=self.product.pk).update(method="")
        body = self.client.get(detail_url(self.product.id)).json()
        self.assertEqual((body["images"], body["thumbnailUrl"], body["method"]), ([], None, None))

    def test_craft_is_null_unless_story_is_public(self):
        url = detail_url(self.product.id)
        self.assertIsNone(self.client.get(url).json()["craft"])  # ストーリーなし
        story = ProducerStory.objects.create(producer=self.producer, craft="こだわり")
        for status in [PublishStatus.DRAFT, PublishStatus.PRIVATE, PublishStatus.SUSPENDED]:
            story.publish_status = status
            story.save()
            with self.subTest(status=status):
                self.assertIsNone(self.client.get(url).json()["craft"])
        story.publish_status = PublishStatus.PUBLIC
        story.craft = ""
        story.save()
        self.assertIsNone(self.client.get(url).json()["craft"])

    def test_is_favorited(self):
        user = make_user(email="buyer@example.com")
        FavoriteProduct.objects.create(user=user, product=self.product)
        self.signin(user.email)
        self.assertTrue(self.client.get(detail_url(self.product.id)).json()["isFavorited"])

    def test_not_public_is_404(self):
        self.product.publish_status = PublishStatus.PRIVATE
        self.product.save()
        # 出品者本人がログインしていても、公開側では見られない
        self.signin(self.producer.user.email)
        for url in [detail_url(self.product.id), detail_url(999999)]:
            res = self.client.get(url)
            self.assertEqual(res.status_code, 404)
            self.assertEqual(res.json(), {"errorCode": "PRODUCT_NOT_FOUND", "errorMsg": "商品が見つかりません。"})

    def test_hidden_producer_is_404(self):
        self.producer.publish_status = PublishStatus.SUSPENDED
        self.producer.save()
        self.assertEqual(self.client.get(detail_url(self.product.id)).status_code, 404)

    def test_non_numeric_or_huge_id_is_404(self):
        res = self.client.get("/api/v1/products/abc")
        self.assertEqual((res.status_code, res.json()["errorCode"]), (404, "NOT_FOUND"))
        res = self.client.get(detail_url(2 ** 63))
        self.assertEqual((res.status_code, res.json()["errorCode"]), (404, "PRODUCT_NOT_FOUND"))

    def test_unknown_query_is_400(self):
        res = self.client.get(detail_url(self.product.id), {"foo": "1"})
        self.assertEqual((res.status_code, res.json()["errorCode"]), (400, "VALIDATION_ERROR"))

    def test_query_count(self):
        add_image(self.product)
        add_image(self.product, sort_order=1)
        ProducerStory.objects.create(producer=self.producer, craft="こだわり", publish_status=PublishStatus.PUBLIC)
        with self.assertNumQueries(4):  # 商品（JOIN とサブクエリ）・画像＋SAVEPOINT・RELEASE
            self.client.get(detail_url(self.product.id))
