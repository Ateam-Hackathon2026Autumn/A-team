"""注文の作成・状態変更

view・バッチから呼ぶ業務ロジック。複数のAPI・バッチで同じ処理を使うものをここにまとめる。

実装済み:
  - create_order(owner, user, guest, address, payment_method, expected_grand_total): 注文を作る（1つのトランザクション）
      カート行 → 商品（商品ID順）をロック → 購入できるか・在庫・合計を確かめ直す → orders（pending）→
      order_shipments（unshipped）→ order_items → 在庫を減らす（stock >= 数量 のときだけ）→ カートを空にする
      409: CART_EMPTY / QUOTE_CHANGED（購入できない明細・在庫不足・合計が変わった）/ CANNOT_PURCHASE_OWN /
           PAYMENT_METHOD_NOT_AVAILABLE（合計が50円未満、コンビニ払いで120円〜30万円の範囲外）
  - checkout_lines(order): Stripe の支払いページに出す明細 [(商品名, 割引後の単価, 数量)]
  - undo_order(order, owner): 支払いページを作れなかったとき、注文を failed にして在庫とカートを元に戻す
  - mark_paid(order_id, payment_intent_id): pending → paid。購入者に注文確定メール（ゲストは閲覧用トークンを作り直して
      メールのURLに載せる）、生産者ごとに新規注文の通知・メール。pending でなければ何もしない（Webhook が2回届いても1回分）
  - save_payment_intent(order_id, payment_intent_id): コンビニ払いの支払い待ちのあいだに PaymentIntent の ID だけ保存
  - fail_order(order_id, reason): pending → failed。在庫を戻し、購入者にメール。pending でなければ何もしない
  - restore_stock(shipment): 箱の明細の数量を在庫に戻す（stock が空＝在庫管理しない商品は何もしない）
  - SHIPMENT_STATE_CONFLICT: 箱の状態が想定と違うときの 409 の errorCode
  - cancellable_producer_ids(order, shipments): 購入者がキャンセルを申請できる生産者の ID
      （注文が paid で、その生産者の箱がすべて unshipped）
  - request_cancel(order_id, producer_id, reason): キャンセル申請。その生産者の箱をまとめて cancel_requested にし、
      生産者に通知・メール。できなければ 409 CANCEL_NOT_ALLOWED、注文にない生産者は 400
  - refund_canceled_shipments(shipment_ids): キャンセルが確定した箱のうち、カード払いの箱を Stripe で返金する
      （キャンセル承認・管理者キャンセルのトランザクションが終わってから呼ぶ。失敗しても返金待ちのまま。ログに残す）
  - refund_by_stripe(shipment_id): 箱1つを Stripe で返金して記録する（管理者返金 method=stripe）
      Stripe で返金できない（コンビニ払い・キーなし）は RefundNotAvailable、Stripe のエラーは payments.PaymentError
  - record_refund(shipment_id, amount, stripe_refund_id): 返金待ちのときだけ refunded_amount・stripe_refund_id を
      書き込み（条件付き更新）、購入者に「返金が完了しました」と通知・メール

使う場所: POST /orders・POST /guest/orders、Webhook、未決済注文の自動キャンセル（バッチ）、mark_order_paid（開発用）、
         注文履歴・詳細・キャンセル申請（会員・ゲスト）、キャンセル承認・拒否、管理者キャンセル・返金
"""
import hashlib
import logging
import secrets

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from marche.models import CartItem, Notification, Order, OrderItem, OrderShipment, Product

from rest_framework.exceptions import ValidationError

from ..common.exceptions import Conflict
from . import mail, payments
from .cart import MAX_QUANTITY, unavailable_reason
from .notifications import notify, notify_order_buyer
from .pricing import group_into_boxes, refund_amount, tax_amounts
from .visibility import public_products

logger = logging.getLogger(__name__)

# 箱の状態が想定と違う（発送済みをもう一度発送、キャンセル済みをもう一度キャンセル など）
SHIPMENT_STATE_CONFLICT = "SHIPMENT_STATE_CONFLICT"

MIN_AMOUNT = 50  # Stripe で決済できる最低金額（円）
KONBINI_MIN, KONBINI_MAX = 120, 300000  # コンビニ払いで払える金額の範囲（円）
TEMPERATURE_LABELS = {"normal": "常温", "chilled": "冷蔵", "frozen": "冷凍"}
GUEST_ORDER_PATH = "/orders/{order_id}"  # ゲストが注文を見る画面。トークンは # の後ろに付ける（サーバーのログに残さない）


def quote_changed():
    return Conflict("QUOTE_CHANGED", "カートの内容・価格・在庫が変わりました。カートを確認してから、もう一度ご注文ください。")


def hash_token(token):
    return hashlib.sha256(token.encode()).hexdigest()


def new_access_token():
    """(トークン, SHA-256) を返す。DB にはハッシュだけを保存し、トークンはメールの URL にだけ載せる"""
    token = secrets.token_urlsafe(32)
    return token, hash_token(token)


def generate_order_no():
    """注文番号 TM-YYYYMMDD-NNNNNN（日本時間の日付＋ランダム6桁）。重なったら作り直す"""
    today = timezone.localdate().strftime("%Y%m%d")
    for _ in range(10):
        order_no = f"TM-{today}-{secrets.randbelow(10 ** 6):06d}"
        if not Order.objects.filter(order_no=order_no).exists():
            return order_no
    raise RuntimeError("注文番号を作れませんでした")


def check_payment_amount(payment_method, grand_total):
    if grand_total < MIN_AMOUNT:
        raise Conflict("PAYMENT_METHOD_NOT_AVAILABLE", f"合計{MIN_AMOUNT}円未満のご注文はお支払いできません。")
    if payment_method == "konbini" and not KONBINI_MIN <= grand_total <= KONBINI_MAX:
        raise Conflict("PAYMENT_METHOD_NOT_AVAILABLE",
                       f"コンビニ払いは合計{KONBINI_MIN:,}円〜{KONBINI_MAX:,}円のご注文でご利用いただけます。")


def create_order(owner, user, guest, address, payment_method, expected_grand_total):
    """注文を作って返す。owner はカートの持ち主（cart_owner() の戻り値）。会員は user、ゲストは guest（連絡先）を渡す

    address・guest はシリアライザーの validated_data（スネークケース）。合計がサーバーの計算と違えば 409 QUOTE_CHANGED。
    """
    if owner is None:
        raise Conflict("CART_EMPTY", "カートに商品がありません。")
    with transaction.atomic():
        cart_items = list(CartItem.objects.select_for_update().filter(**owner).order_by("product_id"))
        if not cart_items:
            raise Conflict("CART_EMPTY", "カートに商品がありません。")
        product_ids = [item.product_id for item in cart_items]
        # 在庫を読む前に商品の行を商品ID順にロックする（同時に注文されても在庫がずれないように）
        list(Product.objects.select_for_update().filter(pk__in=product_ids).order_by("pk").values_list("pk", flat=True))
        products = Product.objects.select_related("producer", "shipping_setting").in_bulk(product_ids)
        public_ids = set(public_products().filter(pk__in=product_ids).values_list("pk", flat=True))

        lines = []
        for item in cart_items:
            item.product = products[item.product_id]
            if user is not None and item.product.producer.user_id == user.pk:
                raise Conflict("CANNOT_PURCHASE_OWN", "ご自身の商品は購入できません。カートから削除してください。")
            if unavailable_reason(item, item.product_id in public_ids):
                raise quote_changed()
            lines.append((item.product, item.product.sale_price * item.quantity, item.id))

        boxes = group_into_boxes(lines)
        items_total = sum(box["items_total"] for box in boxes)
        shipping_total = sum(box["shipping_fee"] for box in boxes)
        grand_total = items_total + shipping_total
        if grand_total != expected_grand_total:
            raise quote_changed()
        check_payment_amount(payment_method, grand_total)

        items_by_id = {item.id: item for item in cart_items}
        tax_lines = [(items_by_id[i].product.tax_rate, items_by_id[i].product.sale_price * items_by_id[i].quantity)
                     for box in boxes for i in box["line_ids"]]
        tax_8, tax_10 = tax_amounts(tax_lines, shipping_total)
        now = timezone.now()
        order = Order.objects.create(
            order_no=generate_order_no(),
            user=user,
            guest_email=guest["email"] if guest else None,
            guest_name=f"{guest['last_name']} {guest['first_name']}" if guest else None,
            guest_phone=guest["phone"] if guest else None,
            access_token_hash=new_access_token()[1],  # 会員の注文もランダムな値（ゲストは支払い確定時に作り直す）
            ship_name=f"{address['last_name']} {address['first_name']}",
            ship_postal_code=address["postal_code"],
            ship_prefecture=address["prefecture"],
            ship_city=address["city"],
            ship_address_line1=address["address_line1"],
            ship_address_line2=address.get("address_line2") or None,
            ship_phone=address["phone"],
            payment_method=payment_method,
            items_total=items_total, shipping_total=shipping_total, grand_total=grand_total,
            tax_8_amount=tax_8, tax_10_amount=tax_10,
            payment_status=Order.PaymentStatus.PENDING,
            ordered_at=now,
        )
        order_items = []
        for box in boxes:
            shipment = OrderShipment.objects.create(
                order=order, producer=box["producer"], temperature_zone=box["setting"].temperature_zone,
                shipping_fee=box["shipping_fee"], status=OrderShipment.Status.UNSHIPPED)
            for item_id in box["line_ids"]:
                item = items_by_id[item_id]
                product = item.product
                order_items.append(OrderItem(
                    shipment=shipment, product=product, product_name=product.name, unit_price=product.price,
                    discount_rate=product.discount_rate, paid_unit_price=product.sale_price, quantity=item.quantity,
                    tax_rate=product.tax_rate, subtotal=product.sale_price * item.quantity))
        OrderItem.objects.bulk_create(order_items)

        for item in cart_items:
            if item.product.stock is None:
                continue  # 在庫管理しない商品
            updated = Product.objects.filter(pk=item.product_id, stock__gte=item.quantity).update(
                stock=F("stock") - item.quantity, updated_at=now)
            if not updated:
                raise quote_changed()
        CartItem.objects.filter(pk__in=[item.id for item in cart_items]).delete()
    return order


def checkout_lines(order):
    """支払いページに出す明細 [(商品名, 割引後の単価, 数量)]（箱の順・明細の順）"""
    items = OrderItem.objects.filter(shipment__order=order).order_by("shipment_id", "id")
    return [(item.product_name, item.paid_unit_price, item.quantity) for item in items]


def undo_order(order, owner):
    """支払いページを作れなかった注文を取り消す：failed にして在庫を戻し、カートに戻す（メールは送らない）"""
    with transaction.atomic():
        if not _fail_locked(order.pk):
            return
        for item in OrderItem.objects.filter(shipment__order=order).order_by("id"):
            cart_item = CartItem.objects.select_for_update().filter(**owner, product_id=item.product_id).first()
            if cart_item:  # そのあいだに同じ商品をカートに入れていた
                cart_item.quantity = min(cart_item.quantity + item.quantity, MAX_QUANTITY)
                cart_item.save(update_fields=["quantity", "updated_at"])
            else:
                CartItem.objects.create(**owner, product_id=item.product_id, quantity=item.quantity)


def _fail_locked(order_id):
    """pending の注文を failed にして在庫を戻す（呼び出し側のトランザクションの中）。変えたら True"""
    order = Order.objects.select_for_update().filter(pk=order_id).first()
    if order is None or order.payment_status != Order.PaymentStatus.PENDING:
        return False
    order.payment_status = Order.PaymentStatus.FAILED
    order.save(update_fields=["payment_status", "updated_at"])
    for shipment in order.order_shipments.prefetch_related("order_items"):
        restore_stock(shipment)
    return True


FAIL_MESSAGES = {
    "expired": "お支払いの期限が過ぎたため、ご注文を取り消しました。",
    "payment_failed": "お支払いが完了しなかったため、ご注文を取り消しました。",
}


def fail_order(order_id, reason="expired"):
    """pending の注文を failed にし、在庫を戻して購入者にメールする。変えたら True"""
    with transaction.atomic():
        if not _fail_locked(order_id):
            return False
        order = Order.objects.select_related("user").get(pk=order_id)
        body = (f"注文番号：{order.order_no}\n\n{FAIL_MESSAGES[reason]}\n"
                "ご購入をご希望の場合は、もう一度カートに商品を入れてご注文ください。\n")
        notify_order_buyer(order, Notification.NotificationType.CANCELED,
                           f"ご注文を取り消しました（注文番号 {order.order_no}）", body, guest_guide=False)
    return True


def save_payment_intent(order_id, payment_intent_id):
    """支払い待ち（コンビニ払い）の注文に PaymentIntent の ID を保存する（まだ入っていないときだけ）"""
    if payment_intent_id:
        Order.objects.filter(pk=order_id, payment_status=Order.PaymentStatus.PENDING,
                             stripe_payment_intent_id__isnull=True).update(
            stripe_payment_intent_id=payment_intent_id, updated_at=timezone.now())


def mark_paid(order_id, payment_intent_id=None):
    """pending の注文を paid にし、購入者と生産者に知らせる。変えたら True"""
    with transaction.atomic():
        order = Order.objects.select_for_update().filter(pk=order_id).first()
        if order is None:
            return False
        if order.payment_status != Order.PaymentStatus.PENDING:
            if order.payment_status == Order.PaymentStatus.FAILED:
                # 取り消したあとに支払われた（通常は起きない）。運営が確認して返金する
                logger.error("取り消し済みの注文に支払いがありました: order_id=%s payment_intent=%s",
                             order_id, payment_intent_id)
            return False
        order.payment_status = Order.PaymentStatus.PAID
        fields = ["payment_status", "updated_at"]
        if payment_intent_id:
            order.stripe_payment_intent_id = payment_intent_id
            fields.append("stripe_payment_intent_id")
        token = None
        if order.user_id is None:
            token, order.access_token_hash = new_access_token()
            fields.append("access_token_hash")
        order.save(update_fields=fields)

        shipments = list(order.order_shipments.select_related("producer__user")
                         .prefetch_related("order_items").order_by("id"))
        _send_paid_mails(order, shipments, token)
    return True


def _box_text(shipments):
    lines = []
    for shipment in shipments:
        zone = TEMPERATURE_LABELS.get(shipment.temperature_zone, shipment.temperature_zone)
        lines.append(f"■ {shipment.producer.business_name}（{zone}）")
        for item in shipment.order_items.all():
            lines.append(f"  {item.product_name} × {item.quantity}  {item.subtotal:,}円")
        lines.append(f"  送料  {shipment.shipping_fee:,}円")
    return "\n".join(lines) + "\n"


def _send_paid_mails(order, shipments, guest_token):
    body = (
        "お支払いを確認しました。ご注文ありがとうございます。\n\n"
        f"注文番号：{order.order_no}\n\n"
        + _box_text(shipments)
        + f"\n商品合計：{order.items_total:,}円\n送料合計：{order.shipping_total:,}円\n"
        f"お支払い合計：{order.grand_total:,}円（税込）\n\n"
        "生産者ごとに発送します。発送されたら、あらためてお知らせします。\n"
    )
    title = f"ご注文ありがとうございます（注文番号 {order.order_no}）"
    if guest_token:
        url = mail.frontend_url(GUEST_ORDER_PATH.format(order_id=order.id)) + f"#token={guest_token}"
        body += ("\nご注文の状況の確認・キャンセルのお申し込みは、次のURLからできます（このメールは大切に保管してください）。\n"
                 f"{url}\n")
    notify_order_buyer(order, Notification.NotificationType.NEW_ORDER, title, body, guest_guide=False)

    by_producer = {}
    for shipment in shipments:
        by_producer.setdefault(shipment.producer_id, []).append(shipment)
    for producer_shipments in by_producer.values():
        producer = producer_shipments[0].producer
        producer_body = (
            "新しい注文が入りました。注文管理画面から発送の準備をお願いします。\n\n"
            f"注文番号：{order.order_no}\n\n" + _box_text(producer_shipments)
        )
        notify(producer.user, Notification.NotificationType.NEW_ORDER,
               f"新しい注文が入りました（注文番号 {order.order_no}）", producer_body)


def restore_stock(shipment):
    """箱の明細の数量を在庫に戻す。呼び出し元のトランザクションの中で使う

    stock が空の商品（在庫管理しない）は戻さない。stock = stock + 数量 を DB 側で計算するので、
    同時に別の注文で在庫が減っても値がずれない。明細は shipment.order_items（prefetch 済みならそれ）を使う。
    """
    now = timezone.now()
    for item in shipment.order_items.all():
        Product.objects.filter(pk=item.product_id, stock__isnull=False).update(
            stock=F("stock") + item.quantity, updated_at=now)


# =========================================================
# キャンセル申請（購入者）
# =========================================================

CANCEL_NOT_ALLOWED = "CANCEL_NOT_ALLOWED"


def cancellable_producer_ids(order, shipments):
    """キャンセルを申請できる生産者の ID の集合。注文が paid で、その生産者の箱がすべて unshipped"""
    if order.payment_status != Order.PaymentStatus.PAID:
        return set()
    statuses = {}
    for shipment in shipments:
        statuses.setdefault(shipment.producer_id, []).append(shipment.status)
    return {producer_id for producer_id, values in statuses.items()
            if all(value == OrderShipment.Status.UNSHIPPED for value in values)}


def request_cancel(order_id, producer_id, reason):
    """その生産者の箱をまとめて cancel_requested にする。注文 → 箱の順にロックしてから状態を確かめる"""
    with transaction.atomic():
        order = Order.objects.select_for_update().get(pk=order_id)
        shipments = list(OrderShipment.objects.select_for_update().filter(order=order, producer_id=producer_id)
                         .select_related("producer__user").order_by("id"))
        if not shipments:
            raise ValidationError({"producer_id": ["この生産者の商品はご注文に含まれていません。"]})
        if order.payment_status != Order.PaymentStatus.PAID:
            raise Conflict(CANCEL_NOT_ALLOWED, "お支払いが完了していない注文はキャンセルできません。")
        if any(shipment.status != OrderShipment.Status.UNSHIPPED for shipment in shipments):
            raise Conflict(CANCEL_NOT_ALLOWED,
                           "発送済み・キャンセル申請中・キャンセル済みの商品があるため、キャンセルを申請できません。")
        for shipment in shipments:
            shipment.status = OrderShipment.Status.CANCEL_REQUESTED
            shipment.cancel_reason = reason
            shipment.save(update_fields=["status", "cancel_reason", "updated_at"])
        producer = shipments[0].producer
        notify(producer.user, Notification.NotificationType.CANCEL_REQUESTED,
               f"キャンセル申請が届きました（注文番号 {order.order_no}）",
               f"注文番号 {order.order_no} のあなたの商品について、購入者からキャンセルの申請がありました。\n"
               f"理由: {reason}\n\n"
               "注文管理画面で、承認または拒否をしてください。承認するまでは発送しないでください。\n")


# =========================================================
# 返金
# =========================================================

class RefundNotAvailable(Exception):
    """この箱は Stripe で返金できない（コンビニ払い・Stripe のキーがない など）"""


def record_refund(shipment_id, amount, stripe_refund_id=None):
    """返金待ち（canceled かつ refunded_amount が空）のときだけ返金を記録し、購入者に知らせる。記録したら True"""
    with transaction.atomic():
        updated = OrderShipment.objects.filter(
            pk=shipment_id, status=OrderShipment.Status.CANCELED, refunded_amount__isnull=True,
        ).update(refunded_amount=amount, stripe_refund_id=stripe_refund_id, updated_at=timezone.now())
        if updated:
            shipment = OrderShipment.objects.select_related("order__user", "producer").get(pk=shipment_id)
            card_note = "カードへの返金は、ご利用明細に反映されるまで数日かかることがあります。\n" if stripe_refund_id else ""
            notify_order_buyer(
                shipment.order, Notification.NotificationType.CANCELED, "返金が完了しました",
                f"ご注文（注文番号 {shipment.order.order_no}）のうち、{shipment.producer.business_name}の商品について、"
                f"{amount:,}円を返金しました。\n{card_note}")
    return bool(updated)


def refund_by_stripe(shipment_id):
    """箱1つを Stripe で返金して記録する。返金待ちでなければ何もせず False"""
    shipment = (OrderShipment.objects.select_related("order").prefetch_related("order_items")
                .get(pk=shipment_id))
    if shipment.status != OrderShipment.Status.CANCELED or shipment.refunded_amount is not None:
        return False
    order = shipment.order
    if order.payment_method != "card":
        raise RefundNotAvailable("コンビニ払いは Stripe で返金できません。")
    if not order.stripe_payment_intent_id:
        raise RefundNotAvailable("Stripe の決済IDがないため返金できません。manual で記録してください。")
    if not payments.is_enabled():
        raise RefundNotAvailable("Stripe が設定されていないため返金できません。manual で記録してください。")
    amount = refund_amount(shipment)
    refund = payments.refund_shipment(order.stripe_payment_intent_id, shipment.id, amount)
    if refund["status"] not in payments.REFUND_OK_STATUSES:
        raise payments.PaymentError(f"返金の状態が {refund['status']} です")
    return record_refund(shipment.id, amount, refund["id"])


def refund_canceled_shipments(shipment_ids):
    """キャンセルが確定した箱のうち、カード払いの箱を Stripe で返金する。できなかった箱は返金待ちのまま（ログに残す）"""
    for shipment_id in shipment_ids:
        try:
            refund_by_stripe(shipment_id)
        except RefundNotAvailable as exc:
            logger.info("Stripe で返金しませんでした（返金待ちのまま）: shipment_id=%s %s", shipment_id, exc)
        except payments.PaymentError:
            logger.error("Stripe の返金に失敗しました（返金待ちのまま）: shipment_id=%s", shipment_id)
