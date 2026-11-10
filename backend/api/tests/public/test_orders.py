"""注文・決済 のテスト

テスト対象: api/views/public/orders.py（services/orders.py の create_order・undo_order、services/pricing.py の税額）
  - 注文・決済（会員）: POST /api/v1/orders
  - 注文・決済（ゲスト）: POST /api/v1/guest/orders
Stripe は呼ばない（services/payments.py の create_checkout_session を差し替える）。
注文履歴・詳細・キャンセル申請はステップ6bで追加する。
"""
from unittest.mock import patch

from django.test import override_settings

from marche.models import CartItem, Order, OrderItem, OrderShipment, PublishStatus, ShippingSetting
from api.services.payments import PaymentError

from ..utils import ApiTestCase, make_prefecture, make_producer, make_product, make_user

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
