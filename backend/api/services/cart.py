"""カートの持ち主の判定・中身の組み立て・付け替え

- cart_owner(request, create=False): 会員は {"user": user}、ゲストは {"session_key": key}。
  ゲストでセッションがまだなければ None（create=True なら作る。カートに追加するときだけ作る）
- build_cart(owner, user): カートの中身（明細・箱ごとの小計と送料・合計・購入できるか）を組み立てる
  - 価格は保存しない。表示のたびに最新の sale_price
  - 購入できない明細は残して purchasable=false と理由を返し、箱と合計には入れない
    PRODUCT_UNAVAILABLE（非公開など。商品名・価格は null）/ UNSUPPORTED_PRODUCT（定期便）
    / OUT_OF_STOCK（在庫0）/ QUANTITY_EXCEEDS_STOCK（数量が在庫より多い）。stock が空は在庫管理しない＝購入可
- merge_guest_cart(): ログイン・新規登録時に、ゲストのときの session_key の行を user_id に付け替える
  （同じ商品は数量を合算し、上限10で切り捨てる）

使う場所: GET・POST・PATCH・DELETE /cart、POST /auth/signin、POST /users、POST /orders（カートを空にする）
"""
from django.db import transaction
from django.db.models import Exists, OuterRef, Subquery

from marche.models import CartItem, ProductImage

from ..common.images import image_url
from .pricing import group_into_boxes
from .visibility import public_products

MAX_QUANTITY = 10
MAX_CART_LINES = 50


def cart_owner(request, create=False):
    """カートの持ち主の条件（CartItem の filter にそのまま渡す）。ゲストでセッションがなければ None"""
    if request.user.is_authenticated:
        return {"user": request.user}
    if request.session.session_key is None:
        if not create:
            return None
        request.session["has_cart"] = True  # 変更があるので、レスポンスでセッションの Cookie が付く
        request.session.save()
    return {"session_key": request.session.session_key}


def unavailable_reason(item, is_public):
    """購入できない理由（購入できるなら None）"""
    product = item.product
    if not is_public:
        return "PRODUCT_UNAVAILABLE"
    if product.is_subscription:
        return "UNSUPPORTED_PRODUCT"
    if product.stock == 0:
        return "OUT_OF_STOCK"
    if product.stock is not None and item.quantity > product.stock:
        return "QUANTITY_EXCEEDS_STOCK"
    return None


def build_cart(owner):
    """カートの中身。owner が None（ゲストでセッションなし）なら空のカート。SQL は明細の1本だけ"""
    items = []
    if owner is not None:
        thumbnail = (ProductImage.objects.filter(product=OuterRef("product_id"))
                     .order_by("sort_order", "id").values("image")[:1])
        items = list(
            CartItem.objects.filter(**owner)
            .select_related("product__producer", "product__shipping_setting")
            .annotate(thumbnail_key=Subquery(thumbnail),
                      is_public=Exists(public_products().filter(pk=OuterRef("product_id"))))
            .order_by("created_at", "id")
        )

    lines, purchasable_lines = [], []
    for item in items:
        product = item.product
        reason = unavailable_reason(item, item.is_public)
        visible = reason != "PRODUCT_UNAVAILABLE"
        subtotal = product.sale_price * item.quantity if visible else None
        lines.append({
            "id": item.id, "product_id": item.product_id,
            "product_name": product.name if visible else None,
            "volume": product.volume if visible else None,
            "thumbnail_url": image_url(item.thumbnail_key) if visible else None,
            "quantity": item.quantity,
            "unit_price": product.sale_price if visible else None,
            "subtotal": subtotal, "purchasable": reason is None, "unavailable_reason": reason,
        })
        if reason is None:
            purchasable_lines.append((product, subtotal, item.id))

    boxes = group_into_boxes(purchasable_lines)
    items_total = sum(box["items_total"] for box in boxes)
    shipping_total = sum(box["shipping_fee"] for box in boxes)
    return {
        "items": lines,
        "shipments": [{
            "producer_id": box["producer"].id, "producer_name": box["producer"].business_name,
            "temperature_zone": box["setting"].temperature_zone, "item_ids": box["line_ids"],
            "items_total": box["items_total"], "shipping_fee": box["shipping_fee"],
            "free_shipping_threshold": box["setting"].free_shipping_threshold,
        } for box in boxes],
        "items_total": items_total,
        "shipping_total": shipping_total,
        "total": items_total + shipping_total,
        "can_checkout": bool(lines) and all(line["purchasable"] for line in lines),
    }


def merge_guest_cart(guest_session_key, user):
    """ゲストのカートを会員のカートに付け替える。

    Django の login() はセッションキーを作り直すので、呼び出し側は login() の前に
    request.session.session_key を控えておき、login() の後にこの関数を呼ぶ。
    戻り値は付け替えた（または合算した）行数。
    """
    if not guest_session_key:
        return 0

    with transaction.atomic():
        guest_items = list(
            CartItem.objects.select_for_update().filter(session_key=guest_session_key, user__isnull=True)
        )
        if not guest_items:
            return 0

        member_items = {
            item.product_id: item
            for item in CartItem.objects.select_for_update().filter(
                user=user, product_id__in=[g.product_id for g in guest_items]
            )
        }

        for guest in guest_items:
            member = member_items.get(guest.product_id)
            if member:
                # 同じ商品が会員のカートにもある：数量を合算（上限10）してゲスト側の行を消す
                member.quantity = min(member.quantity + guest.quantity, MAX_QUANTITY)
                member.save(update_fields=["quantity", "updated_at"])
                guest.delete()
            else:
                guest.user = user
                guest.session_key = None
                guest.save(update_fields=["user", "session_key", "updated_at"])

    return len(guest_items)
