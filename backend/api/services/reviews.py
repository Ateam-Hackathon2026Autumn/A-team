"""商品レビュー（投稿・編集・削除・返信）と評価の集計

view から呼ぶ業務ロジック。購入者側と生産者側で同じものを使う。

レビューを書ける明細（reviewable_items）:
  自分の注文（会員）で支払い済み、その明細の箱が発送済み（shipped）か配達完了（delivered）、まだレビューしていない

実装済み:
  - reviewable_items(user, product_id=None): 書ける明細の QuerySet（新しい順）
  - recalculate_rating(product_id): products.rating_avg・review_count を product_reviews から AVG・COUNT で集計し直す
      （0件なら rating_avg を空。平均は小数第1位で四捨五入）。呼び出し側のトランザクションの中で、商品の行をロックしてから使う
  - create_review(product_id, user, data): 投稿。商品の行をロック → 明細を決める（orderItemId を省略したら書ける明細の
      一番新しいもの）→ 作る → 集計し直す。生産者に通知・メール（new_review）
      書ける明細がない・指定した明細が条件に合わない → 409 REVIEW_NOT_ALLOWED／同じ明細にレビュー済み → 409 ALREADY_REVIEWED／
      ほかの商品の明細 → 400
  - update_review(review_id, user, data) / delete_review(review_id, user): 自分のレビューの編集・削除（集計し直す）。
      他人・存在しないレビューは 404 REVIEW_NOT_FOUND
  - reply_to_review(review_id, producer, reply): 生産者の返信（上書き。空なら削除）。初めて返信したときだけ投稿者に
      サイト内の通知（review_reply。メールなし）

使う場所: api/views/public/reviews.py、api/views/dashboard/reviews.py、注文詳細の reviewable（serializers/public/orders.py）
"""
from decimal import ROUND_HALF_UP, Decimal

from django.db import IntegrityError, transaction
from django.db.models import Avg, Count
from django.utils import timezone
from rest_framework import serializers, status

from marche.models import Notification, Order, OrderItem, OrderShipment, Product, ProductReview

from ..common.exceptions import ApiError, Conflict
from .notifications import create_notification, notify

REVIEWABLE_SHIPMENT = [OrderShipment.Status.SHIPPED, OrderShipment.Status.DELIVERED]
PRODUCER_REVIEWS_PATH = "/dashboard/reviews"
PRODUCT_PATH = "/products/{product_id}"


def review_not_found():
    return ApiError(status.HTTP_404_NOT_FOUND, "REVIEW_NOT_FOUND", "レビューが見つかりません。")


def reviewable_items(user, product_id=None):
    items = OrderItem.objects.filter(
        shipment__order__user=user, shipment__order__payment_status=Order.PaymentStatus.PAID,
        shipment__status__in=REVIEWABLE_SHIPMENT, review__isnull=True)
    if product_id is not None:
        items = items.filter(product_id=product_id)
    return items.order_by("-shipment__order__ordered_at", "-id")


def is_reviewable(item):
    """明細1件が今レビューを書けるか（shipment__order と review を読んでおく）"""
    order = item.shipment.order
    return (order.user_id is not None and order.payment_status == Order.PaymentStatus.PAID
            and item.shipment.status in REVIEWABLE_SHIPMENT and not has_review(item))


def has_review(item):
    try:
        return item.review is not None
    except ProductReview.DoesNotExist:
        return False


def recalculate_rating(product_id):
    stats = ProductReview.objects.filter(product_id=product_id).aggregate(avg=Avg("rating"), count=Count("id"))
    avg = None
    if stats["count"]:
        avg = Decimal(str(stats["avg"])).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    Product.objects.filter(pk=product_id).update(rating_avg=avg, review_count=stats["count"])


def create_review(product_id, user, data):
    with transaction.atomic():
        product = Product.objects.select_for_update().select_related("producer__user").get(pk=product_id)
        order_item_id = data.get("order_item_id")
        if order_item_id is not None:
            item = OrderItem.objects.filter(pk=order_item_id, shipment__order__user=user).first()
            if item is None or item.product_id != product.pk:
                raise serializers.ValidationError({"order_item_id": ["この商品の購入が見つかりません。"]})
            if ProductReview.objects.filter(order_item=item).exists():
                raise Conflict("ALREADY_REVIEWED", "この購入にはすでにレビューを書いています。")
            if not reviewable_items(user, product.pk).filter(pk=item.pk).exists():
                raise Conflict("REVIEW_NOT_ALLOWED", "発送されたあとにレビューを書けます。")
        else:
            item = reviewable_items(user, product.pk).first()
            if item is None:
                raise Conflict("REVIEW_NOT_ALLOWED", "レビューを書けるのは、この商品を購入して発送されたあとです。")
        try:
            with transaction.atomic():
                review = ProductReview.objects.create(order_item=item, product=product, user=user,
                                                      rating=data["rating"], body=data.get("body"))
        except IntegrityError:  # 同じ明細への投稿が同時に来た
            raise Conflict("ALREADY_REVIEWED", "この購入にはすでにレビューを書いています。")
        recalculate_rating(product.pk)
        notify(product.producer.user, Notification.NotificationType.NEW_REVIEW,
               f"「{product.name}」にレビューが届きました",
               f"「{product.name}」に★{review.rating}のレビューが届きました。\n"
               "レビュー一覧の画面で内容を確認し、よろしければ返信してください。\n",
               PRODUCER_REVIEWS_PATH)
    return review


def _lock_own_review(review_id, user):
    """商品 → レビューの順にロックして返す"""
    found = ProductReview.objects.filter(pk=review_id, user=user).values("product_id").first()
    if found is None:
        raise review_not_found()
    Product.objects.select_for_update().filter(pk=found["product_id"]).first()
    return ProductReview.objects.select_for_update().get(pk=review_id)


def update_review(review_id, user, data):
    with transaction.atomic():
        review = _lock_own_review(review_id, user)
        for field, value in data.items():
            setattr(review, field, value)
        review.save()
        recalculate_rating(review.product_id)
    return review


def delete_review(review_id, user):
    with transaction.atomic():
        review = _lock_own_review(review_id, user)
        product_id = review.product_id
        review.delete()
        recalculate_rating(product_id)


def reply_to_review(review_id, producer, reply):
    with transaction.atomic():
        review = (ProductReview.objects.select_for_update().filter(pk=review_id, product__producer=producer)
                  .select_related("product", "user").first())
        if review is None:
            raise review_not_found()
        first_reply = review.reply is None and bool(reply)
        review.reply = reply or None
        review.replied_at = timezone.now() if reply else None
        review.save(update_fields=["reply", "replied_at", "updated_at"])
        if first_reply:
            create_notification(review.user, Notification.NotificationType.REVIEW_REPLY,
                                "レビューに返信が届きました",
                                f"「{review.product.name}」のレビューに、生産者から返信が届きました。\n",
                                PRODUCT_PATH.format(product_id=review.product_id))
    return review
