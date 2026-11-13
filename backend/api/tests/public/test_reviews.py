"""商品レビュー（一覧・投稿・編集・削除） のテスト

テスト対象: api/views/public/reviews.py（services/reviews.py）
  - 商品レビュー一覧・投稿: GET・POST /api/v1/products/:productId/reviews
  - レビュー編集・削除: PATCH・DELETE /api/v1/users/me/reviews/:reviewId
  - 注文詳細の明細の reviewId・reviewable（GET /api/v1/users/me/orders/:orderId）
"""
from datetime import timedelta
from decimal import Decimal

from django.core import mail
from django.utils import timezone

from marche.models import Notification, Order, Product, ProductReview, PublishStatus

from ...services.reviews import recalculate_rating
from ..utils import ApiTestCase, add_shipment, make_order, make_producer, make_product, make_user


def bought(user, product, status="delivered", payment_status=Order.PaymentStatus.PAID, days_ago=0):
    """user が product を買った明細（箱の状態は status）"""
    order = make_order(user=user, payment_status=payment_status,
                       ordered_at=timezone.now() - timedelta(days=days_ago))
    return add_shipment(order, product.producer, items=((product, 1),), status=status).order_items.get()


def review(user, product, rating=4, **kw):
    item = bought(user, product)
    return ProductReview.objects.create(order_item=item, product=product, user=user, rating=rating, **kw)


class ReviewTestCase(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.producer = make_producer(business_name="山田農園")
        self.product = make_product(self.producer, name="にんじん")
        self.user = make_user(email="buyer@example.com", last_name="佐藤", first_name="花子")
        self.url = f"/api/v1/products/{self.product.id}/reviews"

    def assert_rating(self, avg, count):
        product = Product.objects.get(pk=self.product.pk)
        self.assertEqual((product.rating_avg, product.review_count), (avg, count))


class ReviewListTests(ReviewTestCase):
    def test_list(self):
        old = review(make_user(email="a@example.com", first_name="一郎"), self.product, rating=5, body="甘い",
                     reply="ありがとうございます", replied_at=timezone.now())
        ProductReview.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=1))
        new = review(self.user, self.product, rating=3)
        review(self.user, make_product(self.producer, name="別の商品"))
        with self.assertNumQueries(5):  # 公開中の商品か・件数・一覧（投稿者つき）＋SAVEPOINT・RELEASE（未ログインは canReview を調べない）
            res = self.client.get(self.url)
        data = res.json()
        self.assertEqual(([i["id"] for i in data["items"]], data["total"], data["canReview"]), ([new.id, old.id], 2, False))
        self.assertEqual(data["items"][1], {
            "id": old.id, "rating": 5, "body": "甘い", "reviewerName": "一郎", "reply": "ありがとうございます",
            "repliedAt": data["items"][1]["repliedAt"], "createdAt": data["items"][1]["createdAt"],
            "updatedAt": data["items"][1]["updatedAt"]})

    def test_withdrawn_reviewer(self):
        withdrawn = make_user(email="gone@example.com", first_name="")
        review(withdrawn, self.product)
        withdrawn.deleted_at = timezone.now()
        withdrawn.save()
        self.assertEqual(self.client.get(self.url).json()["items"][0]["reviewerName"], "退会ユーザー")

    def test_can_review(self):
        self.signin(self.user.email)
        bought(self.user, self.product, status="unshipped")
        self.assertFalse(self.client.get(self.url).json()["canReview"])
        bought(self.user, self.product, status="shipped")
        self.assertTrue(self.client.get(self.url).json()["canReview"])

    def test_private_product_is_404(self):
        self.product.publish_status = PublishStatus.PRIVATE
        self.product.save()
        res = self.client.get(self.url)
        self.assertEqual((res.status_code, res.json()["errorCode"]), (404, "PRODUCT_NOT_FOUND"))


class ReviewCreateTests(ReviewTestCase):
    def setUp(self):
        super().setUp()
        self.signin(self.user.email)

    def post(self, body):
        with self.captureOnCommitCallbacks(execute=True):
            return self.post_json(self.url, body)

    def test_create_picks_newest_reviewable_item(self):
        older = bought(self.user, self.product, days_ago=3)
        newer = bought(self.user, self.product, status="shipped", days_ago=1)
        res = self.post({"rating": 4, "body": " 甘くておいしい "})
        self.assertEqual(res.status_code, 201, res.json())
        self.assertEqual((res.json()["rating"], res.json()["body"], res.json()["reviewerName"]),
                         (4, "甘くておいしい", "花子"))
        self.assertEqual(ProductReview.objects.get().order_item_id, newer.id)
        self.assert_rating(Decimal("4.0"), 1)
        res = self.post({"rating": 5, "body": ""})  # 2回目は残りの購入（older）に付く
        self.assertEqual(ProductReview.objects.get(pk=res.json()["id"]).order_item_id, older.id)
        self.assertIsNone(res.json()["body"])
        self.assert_rating(Decimal("4.5"), 2)
        notice = Notification.objects.filter(user=self.producer.user).first()
        self.assertEqual((notice.notification_type, notice.link_path), ("new_review", "/dashboard/reviews"))
        self.assertEqual(mail.outbox[0].to, [self.producer.user.email])
        res = self.post({"rating": 5})  # 書ける購入がもうない
        self.assertEqual((res.status_code, res.json()["errorCode"]), (409, "REVIEW_NOT_ALLOWED"))

    def test_create_with_order_item(self):
        item = bought(self.user, self.product)
        self.assertEqual(self.post({"rating": 2, "orderItemId": item.id}).status_code, 201)
        res = self.post({"rating": 2, "orderItemId": item.id})
        self.assertEqual((res.status_code, res.json()["errorCode"]), (409, "ALREADY_REVIEWED"))

    def test_not_allowed(self):
        cases = [bought(self.user, self.product, status="unshipped"),
                 bought(self.user, self.product, status="cancel_requested"),
                 bought(self.user, self.product, status="canceled"),
                 bought(self.user, self.product, payment_status=Order.PaymentStatus.PENDING)]
        for item in cases:
            res = self.post({"rating": 3, "orderItemId": item.id})
            self.assertEqual((res.status_code, res.json()["errorCode"]), (409, "REVIEW_NOT_ALLOWED"))
        self.assertEqual(self.post({"rating": 3}).status_code, 409)
        self.assert_rating(None, 0)

    def test_other_item_is_400(self):
        other_product = bought(self.user, make_product(self.producer, name="別の商品"))
        theirs = bought(make_user(email="other@example.com"), self.product)
        for item in [other_product, theirs]:
            res = self.post({"rating": 3, "orderItemId": item.id})
            self.assertEqual((res.status_code, set(res.json()["details"])), (400, {"orderItemId"}))

    def test_validation_and_login(self):
        bought(self.user, self.product)
        for body, key in [({"rating": 0}, "rating"), ({"rating": 6}, "rating"), ({}, "rating"),
                          ({"rating": 3, "body": "あ" * 1001}, "body"), ({"rating": 3, "title": "x"}, "title")]:
            res = self.post(body)
            self.assertEqual(res.status_code, 400, body)
            self.assertIn(key, res.json()["details"])
        self.post_json("/api/v1/auth/signout")
        self.assertEqual(self.post({"rating": 3}).status_code, 401)

    def test_private_product_is_404(self):
        bought(self.user, self.product)
        self.product.publish_status = PublishStatus.PRIVATE
        self.product.save()
        self.assertEqual(self.post({"rating": 3}).status_code, 404)


class MyReviewTests(ReviewTestCase):
    def setUp(self):
        super().setUp()
        self.signin(self.user.email)
        self.review = review(self.user, self.product, rating=2, body="ふつう")
        review(make_user(email="other@example.com"), self.product, rating=4)
        recalculate_rating(self.product.pk)
        self.url = f"/api/v1/users/me/reviews/{self.review.id}"

    def test_update(self):
        self.assert_rating(Decimal("3.0"), 2)
        res = self.patch_json(self.url, {"rating": 5})
        self.assertEqual((res.status_code, res.json()["rating"], res.json()["body"]), (200, 5, "ふつう"))
        self.assert_rating(Decimal("4.5"), 2)
        self.assertEqual(self.patch_json(self.url, {}).status_code, 400)

    def test_delete(self):
        self.assertEqual(self.delete_json(self.url).status_code, 204)
        self.assert_rating(Decimal("4.0"), 1)
        ProductReview.objects.all().delete()
        recalculate_rating(self.product.pk)
        self.assert_rating(None, 0)

    def test_private_product_can_still_be_edited(self):
        self.product.publish_status = PublishStatus.PRIVATE
        self.product.save()
        self.assertEqual(self.patch_json(self.url, {"body": "直しました"}).status_code, 200)

    def test_others_review_is_404(self):
        theirs = ProductReview.objects.exclude(pk=self.review.pk).get()
        for review_id in [theirs.id, 999999, 2 ** 63]:
            url = f"/api/v1/users/me/reviews/{review_id}"
            for res in [self.patch_json(url, {"rating": 1}), self.delete_json(url)]:
                self.assertEqual((res.status_code, res.json()["errorCode"]), (404, "REVIEW_NOT_FOUND"))


class OrderDetailReviewFieldsTests(ReviewTestCase):
    def test_review_fields(self):
        self.signin(self.user.email)
        order = make_order(user=self.user)
        shipped = add_shipment(order, self.producer, items=((self.product, 1),), status="shipped")
        add_shipment(order, self.producer, items=((None, 1),), temperature_zone="frozen")  # 未発送
        written = ProductReview.objects.create(order_item=shipped.order_items.get(), product=self.product,
                                               user=self.user, rating=5)
        items = [i for s in self.client.get(f"/api/v1/users/me/orders/{order.id}").json()["shipments"]
                 for i in s["items"]]
        self.assertEqual([(i["reviewId"], i["reviewable"]) for i in items], [(written.id, False), (None, False)])
        ProductReview.objects.all().delete()
        items = self.client.get(f"/api/v1/users/me/orders/{order.id}").json()["shipments"][0]["items"]
        self.assertEqual((items[0]["reviewId"], items[0]["reviewable"]), (None, True))
