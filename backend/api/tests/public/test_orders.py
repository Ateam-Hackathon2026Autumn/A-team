"""注文・決済 のテスト

テスト対象: api/views/public/orders.py（services/orders.py の create_order・undo_order、services/pricing.py の税額）
  - 注文・決済（会員）: POST /api/v1/orders
  - 注文・決済（ゲスト）: POST /api/v1/guest/orders
Stripe は呼ばない（services/payments.py の create_checkout_session を差し替える）。
  - 注文履歴一覧: GET /api/v1/users/me/orders
  - 注文詳細・キャンセル申請（会員）: GET /api/v1/users/me/orders/:orderId・POST .../cancel
  - 注文詳細・キャンセル申請（ゲスト）: GET /api/v1/orders/:orderId・POST .../cancel（X-Order-Token）
"""
from datetime import timedelta
from unittest.mock import patch

from django.core import mail
from django.test import override_settings
from django.utils import timezone

from marche.models import CartItem, Notification, Order, OrderItem, OrderShipment, PublishStatus, ShippingSetting
from api.services.orders import new_access_token
from api.services.payments import PaymentError

from ..utils import ApiTestCase, add_shipment, make_order, make_prefecture, make_producer, make_product, make_user

ORDERS_URL = "/api/v1/orders"
GUEST_ORDERS_URL = "/api/v1/guest/orders"
ADDRESS = {
    "lastName": "佐藤", "firstName": "花子", "postalCode": "1000001", "prefecture": "東京都",
    "city": "千代田区", "addressLine1": "千代田1-1", "addressLine2": "マルシェビル101", "phone": "03-1234-5678",
}
GUEST = {"lastName": "鈴木", "firstName": "一郎", "email": " Ichiro@Example.com ", "phone": "090-1234-5678"}
SESSION = {"id": "cs_test_1", "url": "https://checkout.stripe.com/c/pay/cs_test_1", "expires_at": 1893456000}


def body(total, method="card", **kw):
    data = {"shippingAddress": ADDRESS, "paymentMethod": method, "expectedGrandTotal": total}
    data.update(kw)
    return data


@override_settings(STRIPE_SECRET_KEY="sk_test_dummy")
class OrderTestCase(ApiTestCase):
    def setUp(self):
        super().setUp()
        make_prefecture()
        self.producer = make_producer(business_name="山田農園")
        self.product = make_product(self.producer, name="にんじん", price=1000, stock=5)
        self.checkout = patch("api.services.payments.create_checkout_session", return_value=SESSION).start()
        self.addCleanup(patch.stopall)

    def add(self, product, quantity=1):
        return self.post_json("/api/v1/cart/items", {"productId": product.id, "quantity": quantity})

    def error(self, res):
        return res.status_code, res.json()["errorCode"]


# =========================================================
# 会員
# =========================================================

class MemberOrderTests(OrderTestCase):
    def setUp(self):
        super().setUp()
        self.user = make_user(email="buyer@example.com")  # メール未確認のまま注文できる
        self.signin(self.user.email)

    def test_create_order(self):
        self.add(self.product, 2)  # 1,000円×2＋送料1,000円
        res = self.post_json(ORDERS_URL, body(3000))
        self.assertEqual(res.status_code, 201)
        order = Order.objects.get()
        self.assertEqual(res.json(), {
            "id": order.id, "orderNo": order.order_no, "paymentStatus": "pending", "itemsTotal": 2000,
            "shippingTotal": 1000, "grandTotal": 3000, "checkoutUrl": SESSION["url"],
            "expiresAt": "2030-01-01T09:00:00+09:00",
        })
        self.assertRegex(order.order_no, r"^TM-\d{8}-\d{6}$")
        self.assertEqual(order.user, self.user)
        self.assertIsNone(order.guest_email)
        self.assertEqual(len(order.access_token_hash), 64)
        self.assertEqual(order.stripe_checkout_session_id, "cs_test_1")
        self.assertIsNone(order.stripe_payment_intent_id)
        self.assertEqual((order.tax_8_amount, order.tax_10_amount), (2000 * 8 // 108, 1000 * 10 // 110))
        self.assertEqual((order.ship_name, order.ship_postal_code, order.ship_prefecture, order.ship_phone,
                          order.ship_address_line2), ("佐藤 花子", "100-0001", "東京都", "0312345678", "マルシェビル101"))

        shipment = OrderShipment.objects.get()
        self.assertEqual((shipment.producer, shipment.temperature_zone, shipment.shipping_fee, shipment.status),
                         (self.producer, "normal", 1000, "unshipped"))
        item = OrderItem.objects.get()
        self.assertEqual((item.product_name, item.unit_price, item.paid_unit_price, item.quantity, item.subtotal,
                          item.tax_rate), ("にんじん", 1000, 1000, 2, 2000, 8))

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)
        self.assertFalse(CartItem.objects.exists())
        called_order, lines, email = self.checkout.call_args.args
        self.assertEqual((called_order.id, lines, email), (order.id, [("にんじん", 1000, 2)], "buyer@example.com"))

    def test_boxes_discount_free_shipping_and_unmanaged_stock(self):
        chilled = ShippingSetting.objects.create(producer=self.producer, temperature_zone="chilled", shipping_fee=1200,
                                                 free_shipping_threshold=3000, lead_time_text="翌日発送")
        fish = make_product(self.producer, name="あじ", price=2000, discount_rate=25, shipping_setting=chilled,
                            stock=None)  # 割引後1,500円、在庫管理しない
        other = make_producer(business_name="海風水産")
        rice = make_product(other, name="米", price=3000, tax_rate=10, stock=1)
        self.add(self.product, 1)
        self.add(fish, 2)   # 3,000円 → 送料無料
        self.add(rice, 1)
        # 商品 1,000＋3,000＋3,000 ＝ 7,000、送料 1,000（常温）＋0（冷蔵）＋1,000（海風水産）＝ 2,000
        res = self.post_json(ORDERS_URL, body(9000))
        self.assertEqual(res.status_code, 201, res.json())
        order = Order.objects.get()
        self.assertEqual((order.items_total, order.shipping_total, order.grand_total), (7000, 2000, 9000))
        # 8%: 1,000＋3,000、10%: 米3,000＋送料2,000
        self.assertEqual((order.tax_8_amount, order.tax_10_amount), (4000 * 8 // 108, 5000 * 10 // 110))
        fees = {(s.producer_id, s.temperature_zone): s.shipping_fee for s in order.order_shipments.all()}
        self.assertEqual(fees, {(self.producer.id, "normal"): 1000, (self.producer.id, "chilled"): 0,
                                (other.id, "normal"): 1000})
        fish_item = OrderItem.objects.get(product=fish)
        self.assertEqual((fish_item.unit_price, fish_item.discount_rate, fish_item.paid_unit_price,
                          fish_item.subtotal), (2000, 25, 1500, 3000))
        fish.refresh_from_db()
        rice.refresh_from_db()
        self.assertIsNone(fish.stock)
        self.assertEqual(rice.stock, 0)
        lines = self.checkout.call_args.args[1]
        self.assertEqual(sum(price * quantity for _, price, quantity in lines), 7000)

    def test_requires_login(self):
        self.client.logout()
        res = self.post_json(ORDERS_URL, body(2000))
        self.assertEqual(self.error(res), (401, "NOT_AUTHENTICATED"))

    def test_requires_csrf(self):
        self.add(self.product)
        res = self.post_json(ORDERS_URL, body(2000), csrf=False)
        self.assertEqual(self.error(res), (403, "CSRF_FAILED"))
        self.assertFalse(Order.objects.exists())

    def test_empty_cart(self):
        self.assertEqual(self.error(self.post_json(ORDERS_URL, body(0))), (409, "CART_EMPTY"))

    def test_second_submit_finds_empty_cart(self):
        self.add(self.product)
        self.assertEqual(self.post_json(ORDERS_URL, body(2000)).status_code, 201)
        self.assertEqual(self.error(self.post_json(ORDERS_URL, body(2000))), (409, "CART_EMPTY"))
        self.assertEqual(Order.objects.count(), 1)

    def assert_nothing_changed(self, stock=5):
        self.assertFalse(Order.objects.exists())
        self.assertTrue(CartItem.objects.exists())
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, stock)
        self.checkout.assert_not_called()

    def test_total_changed(self):
        self.add(self.product)
        self.product.price = 1200
        self.product.save()
        self.assertEqual(self.error(self.post_json(ORDERS_URL, body(2000))), (409, "QUOTE_CHANGED"))
        self.assert_nothing_changed()

    def test_product_no_longer_public(self):
        self.add(self.product)
        self.product.publish_status = PublishStatus.PRIVATE
        self.product.save()
        self.assertEqual(self.error(self.post_json(ORDERS_URL, body(2000))), (409, "QUOTE_CHANGED"))
        self.assert_nothing_changed()

    def test_producer_suspended(self):
        self.add(self.product)
        self.producer.publish_status = PublishStatus.SUSPENDED
        self.producer.save()
        self.assertEqual(self.error(self.post_json(ORDERS_URL, body(2000))), (409, "QUOTE_CHANGED"))

    def test_not_enough_stock(self):
        self.add(self.product, 3)
        self.product.stock = 2
        self.product.save()
        self.assertEqual(self.error(self.post_json(ORDERS_URL, body(4000))), (409, "QUOTE_CHANGED"))
        self.assert_nothing_changed(stock=2)

    def test_subscription_product(self):
        self.add(self.product)
        self.product.is_subscription = True
        self.product.save()
        self.assertEqual(self.error(self.post_json(ORDERS_URL, body(2000))), (409, "QUOTE_CHANGED"))

    def test_own_product(self):
        mine = make_product(make_producer(user=self.user, business_name="自分の農園"), price=500)
        CartItem.objects.create(user=self.user, product=mine, quantity=1)  # 生産者になる前に入れていた
        self.assertEqual(self.error(self.post_json(ORDERS_URL, body(1500))), (409, "CANNOT_PURCHASE_OWN"))

    def test_payment_amount_limits(self):
        cheap = make_product(make_producer(business_name="安い農園"), name="小さい苗", price=10)
        ShippingSetting.objects.filter(producer=cheap.producer).update(shipping_fee=0)
        CartItem.objects.create(user=self.user, product=cheap, quantity=4)  # 合計40円
        self.assertEqual(self.error(self.post_json(ORDERS_URL, body(40))), (409, "PAYMENT_METHOD_NOT_AVAILABLE"))
        CartItem.objects.filter(product=cheap).update(quantity=10)  # 合計100円：カードは可、コンビニは不可
        self.assertEqual(self.error(self.post_json(ORDERS_URL, body(100, method="konbini"))),
                         (409, "PAYMENT_METHOD_NOT_AVAILABLE"))
        self.assertEqual(self.post_json(ORDERS_URL, body(100)).status_code, 201)

    def test_konbini(self):
        self.add(self.product)
        self.assertEqual(self.post_json(ORDERS_URL, body(2000, method="konbini")).status_code, 201)
        self.assertEqual(Order.objects.get().payment_method, "konbini")

    def test_stripe_error_restores_stock_and_cart(self):
        self.add(self.product, 2)
        self.checkout.side_effect = PaymentError("down")
        res = self.post_json(ORDERS_URL, body(3000))
        self.assertEqual(self.error(res), (503, "PAYMENT_UNAVAILABLE"))
        order = Order.objects.get()
        self.assertEqual(order.payment_status, "failed")
        self.assertIsNone(order.stripe_checkout_session_id)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)
        self.assertEqual(list(CartItem.objects.values_list("user", "product", "quantity")),
                         [(self.user.id, self.product.id, 2)])

    @override_settings(STRIPE_SECRET_KEY="")
    def test_without_stripe_key(self):
        self.add(self.product)
        self.assertEqual(self.error(self.post_json(ORDERS_URL, body(2000))), (503, "PAYMENT_UNAVAILABLE"))
        self.assert_nothing_changed()

    @override_settings(STRIPE_SECRET_KEY="", DEBUG=True, FRONTEND_BASE_URL="http://localhost:5173")
    def test_without_stripe_key_in_debug(self):
        self.add(self.product)
        with self.assertLogs("api.views.public.orders", "WARNING"):
            res = self.post_json(ORDERS_URL, body(2000))
        self.assertEqual(res.status_code, 201)
        order = Order.objects.get()
        self.assertEqual(res.json()["checkoutUrl"], f"http://localhost:5173/checkout/complete?orderId={order.id}")
        self.assertEqual(order.payment_status, "pending")
        self.checkout.assert_not_called()

    def test_validation(self):
        self.add(self.product)
        res = self.post_json(ORDERS_URL, {
            "shippingAddress": {**ADDRESS, "postalCode": "12-34567", "prefecture": "東京", "phone": "12345"},
            "paymentMethod": "paypay", "expectedGrandTotal": -1,
        })
        self.assertEqual(res.status_code, 400)
        self.assertEqual(set(res.json()["details"]), {
            "shippingAddress.postalCode", "shippingAddress.prefecture", "shippingAddress.phone",
            "paymentMethod", "expectedGrandTotal"})
        self.assertFalse(Order.objects.exists())

    def test_unknown_fields(self):
        self.add(self.product)
        res = self.post_json(ORDERS_URL, body(2000, quoteToken="x"))
        self.assertEqual(set(res.json()["details"]), {"quoteToken"})
        res = self.post_json(ORDERS_URL, body(2000, shippingAddress={**ADDRESS, "nickname": "x"}))
        self.assertEqual(set(res.json()["details"]), {"shippingAddress.nickname"})
        self.assertFalse(Order.objects.exists())

    def test_guest_endpoint_rejects_member(self):
        self.add(self.product)
        res = self.post_json(GUEST_ORDERS_URL, body(2000, guestContact=GUEST))
        self.assertEqual(self.error(res), (409, "ALREADY_AUTHENTICATED"))


# =========================================================
# ゲスト
# =========================================================

class GuestOrderTests(OrderTestCase):
    def test_create_guest_order(self):
        self.add(self.product)
        res = self.post_json(GUEST_ORDERS_URL, body(2000, guestContact=GUEST))
        self.assertEqual(res.status_code, 201, res.json())
        self.assertNotIn("token", str(res.json()).lower())  # 閲覧用トークンはレスポンスに出さない
        order = Order.objects.get()
        self.assertIsNone(order.user)
        self.assertEqual((order.guest_name, order.guest_email, order.guest_phone),
                         ("鈴木 一郎", "ichiro@example.com", "09012345678"))
        self.assertFalse(CartItem.objects.exists())
        self.assertEqual(self.checkout.call_args.args[2], "ichiro@example.com")

    def test_guest_without_cart_session(self):
        res = self.post_json(GUEST_ORDERS_URL, body(2000, guestContact=GUEST))
        self.assertEqual(self.error(res), (409, "CART_EMPTY"))

    def test_guest_contact_required(self):
        self.add(self.product)
        res = self.post_json(GUEST_ORDERS_URL, body(2000))
        self.assertEqual(res.status_code, 400)
        self.assertIn("guestContact", res.json()["details"])

    def test_guest_name_length(self):
        self.add(self.product)
        res = self.post_json(GUEST_ORDERS_URL, body(2000, guestContact={**GUEST, "lastName": "あ" * 50,
                                                                          "firstName": "い" * 50}))
        self.assertEqual(res.status_code, 400)
        self.assertIn("guestContact.firstName", res.json()["details"])

    def test_member_endpoint_rejects_guest(self):
        self.add(self.product)
        self.assertEqual(self.error(self.post_json(ORDERS_URL, body(2000))), (401, "NOT_AUTHENTICATED"))

    def test_stripe_error_restores_guest_cart(self):
        self.add(self.product, 2)
        session_key = CartItem.objects.get().session_key
        self.checkout.side_effect = PaymentError("down")
        res = self.post_json(GUEST_ORDERS_URL, body(3000, guestContact=GUEST))
        self.assertEqual(self.error(res), (503, "PAYMENT_UNAVAILABLE"))
        self.assertEqual(list(CartItem.objects.values_list("session_key", "quantity")), [(session_key, 2)])
        self.assertEqual(self.client.get("/api/v1/cart").json()["items"][0]["quantity"], 2)


# =========================================================
# 注文履歴・詳細・キャンセル申請
# =========================================================

class OrderHistoryTestCase(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.yamada = make_producer(business_name="山田農園")
        self.kaze = make_producer(business_name="海風水産")
        self.buyer = make_user(email="buyer@example.com")
        self.carrot = make_product(self.yamada, name="にんじん", price=1000)

    def paid_order(self, **kw):
        """山田農園の箱2つ（常温・冷凍）と海風水産の箱1つの注文"""
        order = make_order(user=self.buyer, **kw)
        add_shipment(order, self.yamada, items=((self.carrot, 2),))
        add_shipment(order, self.yamada, temperature_zone="frozen", shipping_fee=1500)
        add_shipment(order, self.kaze, shipping_fee=800)
        return order


class MyOrderListTests(OrderHistoryTestCase):
    URL = "/api/v1/users/me/orders"

    def test_list(self):
        self.signin(self.buyer.email)
        old = self.paid_order(ordered_at=timezone.now() - timedelta(days=3))
        new = make_order(user=self.buyer, payment_status="pending", payment_method="konbini")
        add_shipment(new, self.kaze)
        make_order(user=make_user(email="other@example.com"))                 # 他人の注文
        make_order(guest_email="buyer@example.com")                           # 同じメールのゲスト注文は含めない
        with self.assertNumQueries(7):  # セッション・ユーザー・件数・一覧・箱＋SAVEPOINT・RELEASE（箱が増えても変わらない）
            res = self.client.get(self.URL)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual((data["total"], [item["id"] for item in data["items"]]), (2, [new.id, old.id]))
        self.assertEqual(data["items"][0]["paymentMethod"], "konbini")
        first = data["items"][1]
        self.assertEqual(set(first), {"id", "orderNo", "paymentStatus", "paymentMethod", "itemsTotal",
                                      "shippingTotal", "grandTotal", "orderedAt", "shipments"})
        self.assertEqual(first["shipments"][0], {
            "id": first["shipments"][0]["id"], "producerId": self.yamada.id, "producerName": "山田農園",
            "temperatureZone": "normal", "status": "unshipped", "shippingFee": 1000})
        self.assertEqual(len(first["shipments"]), 3)

    def test_filter_and_paging(self):
        self.signin(self.buyer.email)
        self.paid_order()
        make_order(user=self.buyer, payment_status="failed")
        res = self.client.get(self.URL, {"paymentStatus": "failed", "pageSize": 1})
        self.assertEqual((res.json()["total"], res.json()["items"][0]["paymentStatus"]), (1, "failed"))
        self.assertEqual(self.client.get(self.URL, {"paymentStatus": "refunded"}).status_code, 400)
        self.assertEqual(self.client.get(self.URL, {"page": 9}).json()["items"], [])

    def test_requires_login(self):
        self.assertEqual(self.client.get(self.URL).status_code, 401)


class MyOrderDetailTests(OrderHistoryTestCase):
    def url(self, order_id):
        return f"/api/v1/users/me/orders/{order_id}"

    def test_detail(self):
        self.signin(self.buyer.email)
        order = self.paid_order()
        OrderShipment.objects.filter(order=order, producer=self.kaze).update(status="shipped", tracking_no="1234")
        with self.assertNumQueries(5):  # セッション・ユーザー・注文・箱（生産者つき）・明細
            res = self.client.get(self.url(order.id))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual((data["orderNo"], data["tax8Amount"], data["tax10Amount"]),
                         (order.order_no, order.tax_8_amount, order.tax_10_amount))
        self.assertEqual(data["shippingAddress"]["name"], order.ship_name)
        self.assertNotIn("buyer", data)
        box = data["shipments"][0]
        self.assertEqual(box["producer"], {"id": self.yamada.id, "businessName": "山田農園"})
        self.assertEqual(box["items"][0]["productName"], "にんじん")
        self.assertEqual([s["cancellable"] for s in data["shipments"]], [True, True, False])  # 海風水産は発送済み
        self.assertEqual(data["shipments"][2]["trackingNo"], "1234")

    def test_not_cancellable_before_payment(self):
        self.signin(self.buyer.email)
        order = self.paid_order(payment_status="pending")
        self.assertFalse(any(s["cancellable"] for s in self.client.get(self.url(order.id)).json()["shipments"]))

    def test_others_order_is_404(self):
        order = self.paid_order()
        self.signin(make_user(email="other@example.com").email)
        for order_id in [order.id, 999999, 2 ** 63]:
            res = self.client.get(self.url(order_id))
            self.assertEqual((res.status_code, res.json()["errorCode"]), (404, "ORDER_NOT_FOUND"))


class MyOrderCancelTests(OrderHistoryTestCase):
    def url(self, order_id):
        return f"/api/v1/users/me/orders/{order_id}/cancel"

    def setUp(self):
        super().setUp()
        self.signin(self.buyer.email)
        self.order = self.paid_order()

    def test_cancel_request(self):
        with self.captureOnCommitCallbacks(execute=True):
            res = self.post_json(self.url(self.order.id), {"producerId": self.yamada.id,
                                                            "cancelReason": "  注文を間違えました  "})
        self.assertEqual(res.status_code, 200)
        statuses = {(s["producer"]["id"], s["status"], s["cancellable"]) for s in res.json()["shipments"]}
        self.assertEqual(statuses, {(self.yamada.id, "cancel_requested", False),
                                    (self.kaze.id, "unshipped", True)})
        boxes = OrderShipment.objects.filter(order=self.order, producer=self.yamada)
        self.assertEqual(set(boxes.values_list("cancel_reason", flat=True)), {"注文を間違えました"})
        notice = Notification.objects.get(user=self.yamada.user)
        self.assertEqual(notice.notification_type, "cancel_requested")
        self.assertIn("注文を間違えました", mail.outbox[0].body)
        self.assertEqual(mail.outbox[0].to, [self.yamada.user.email])

    def test_not_allowed(self):
        OrderShipment.objects.filter(order=self.order, producer=self.yamada, temperature_zone="frozen") \
            .update(status="shipped")
        cases = [self.order]
        pending = self.paid_order(payment_status="pending")
        cases.append(pending)
        for order in cases:
            res = self.post_json(self.url(order.id), {"producerId": self.yamada.id, "cancelReason": "理由"})
            self.assertEqual((res.status_code, res.json()["errorCode"]), (409, "CANCEL_NOT_ALLOWED"))
        self.post_json(self.url(self.order.id), {"producerId": self.kaze.id, "cancelReason": "理由"})
        res = self.post_json(self.url(self.order.id), {"producerId": self.kaze.id, "cancelReason": "理由"})
        self.assertEqual(res.status_code, 409)  # 申請済み
        self.assertEqual(OrderShipment.objects.filter(status="cancel_requested").count(), 1)

    def test_validation(self):
        other = make_producer(business_name="別の農園")
        res = self.post_json(self.url(self.order.id), {"producerId": other.id, "cancelReason": "理由"})
        self.assertEqual((res.status_code, set(res.json()["details"])), (400, {"producerId"}))
        res = self.post_json(self.url(self.order.id), {"producerId": self.yamada.id, "cancelReason": "あ" * 501})
        self.assertEqual(set(res.json()["details"]), {"cancelReason"})
        res = self.post_json(self.url(self.order.id), {"producerId": self.yamada.id, "cancelReason": "   "})
        self.assertEqual(set(res.json()["details"]), {"cancelReason"})
        self.assertFalse(OrderShipment.objects.filter(status="cancel_requested").exists())

    def test_suspended_producer_can_receive_request(self):
        self.yamada.publish_status = PublishStatus.SUSPENDED
        self.yamada.save()
        res = self.post_json(self.url(self.order.id), {"producerId": self.yamada.id, "cancelReason": "理由"})
        self.assertEqual(res.status_code, 200)

    def test_others_order_is_404(self):
        other_order = make_order(user=make_user(email="other@example.com"))
        add_shipment(other_order, self.yamada)
        res = self.post_json(self.url(other_order.id), {"producerId": self.yamada.id, "cancelReason": "理由"})
        self.assertEqual((res.status_code, res.json()["errorCode"]), (404, "ORDER_NOT_FOUND"))


class GuestOrderTokenTests(OrderHistoryTestCase):
    def setUp(self):
        super().setUp()
        self.token, token_hash = new_access_token()
        self.order = make_order(guest_email="guest@example.com")
        Order.objects.filter(pk=self.order.pk).update(access_token_hash=token_hash, guest_name="鈴木 一郎",
                                                      guest_phone="09012345678")
        add_shipment(self.order, self.yamada)

    def get(self, order_id, token):
        headers = {"HTTP_X_ORDER_TOKEN": token} if token is not None else {}
        return self.client.get(f"/api/v1/orders/{order_id}", **headers)

    def test_detail(self):
        res = self.get(self.order.id, self.token)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["buyer"], {"name": "鈴木 一郎", "email": "guest@example.com",
                                               "phone": "09012345678"})
        self.assertTrue(res.json()["shipments"][0]["cancellable"])

    def test_wrong_token_is_404(self):
        member_token, member_hash = new_access_token()
        member_order = make_order(user=self.buyer)
        Order.objects.filter(pk=member_order.pk).update(access_token_hash=member_hash)
        cases = [(self.order.id, None), (self.order.id, ""), (self.order.id, "x" * 43), (self.order.id, "a" * 201),
                 (member_order.id, member_token), (2 ** 63, self.token)]
        for order_id, token in cases:
            res = self.get(order_id, token)
            self.assertEqual((res.status_code, res.json()["errorCode"]), (404, "ORDER_NOT_FOUND"), token)

    def test_works_while_signed_in(self):
        self.signin(self.buyer.email)
        self.assertEqual(self.get(self.order.id, self.token).status_code, 200)

    def test_cancel(self):
        url = f"/api/v1/orders/{self.order.id}/cancel"
        body = {"producerId": self.yamada.id, "cancelReason": "届け先を間違えました"}
        self.assertEqual(self.post_json(url, body, HTTP_X_ORDER_TOKEN="wrong").status_code, 404)
        res = self.post_json(url, body, HTTP_X_ORDER_TOKEN=self.token)
        self.assertEqual((res.status_code, res.json()["shipments"][0]["status"]), (200, "cancel_requested"))
        self.assertIn("buyer", res.json())
        self.assertEqual(self.post_json(url, body, HTTP_X_ORDER_TOKEN=self.token, csrf=False).status_code, 403)
