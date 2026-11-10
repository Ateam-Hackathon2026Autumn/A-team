"""注文まわりのバッチ・コマンド・Stripe 連携の単体テスト

  - 未決済注文の自動キャンセル: python manage.py cancel_unpaid_orders（marche/management/commands）
  - 開発用：支払い済みにする: python manage.py mark_order_paid
  - services/payments.py の create_checkout_session が Stripe に渡す内容
  - services/orders.py の注文番号
Stripe は呼ばない（payments の関数、または stripe.checkout.Session を差し替える）。
"""
from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.core import mail
from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from marche.models import Order

from ...services import orders, payments
from ..utils import add_shipment, make_order, make_producer, make_product, make_user


def session(status, payment_status="unpaid", payment_intent=None):
    return {"id": "cs_1", "status": status, "payment_status": payment_status, "payment_intent": payment_intent,
            "order_id": None}


@override_settings(STRIPE_SECRET_KEY="sk_test_dummy")
class CancelUnpaidOrdersTests(TestCase):
    def setUp(self):
        self.producer = make_producer()
        self.product = make_product(self.producer, stock=3)
        self.buyer = make_user(email="buyer@example.com")
        self.retrieve = patch("api.services.payments.retrieve_checkout_session").start()
        self.expire = patch("api.services.payments.expire_checkout_session").start()
        self.addCleanup(patch.stopall)

    def order(self, minutes=40, session_id="cs_1", **kw):
        order = make_order(user=self.buyer, payment_status=Order.PaymentStatus.PENDING,
                           ordered_at=timezone.now() - timedelta(minutes=minutes),
                           stripe_checkout_session_id=session_id, **kw)
        add_shipment(order, self.producer, items=((self.product, 2),))
        return order

    def run_batch(self):
        out = StringIO()
        with self.captureOnCommitCallbacks(execute=True):
            call_command("cancel_unpaid_orders", stdout=out)
        return out.getvalue()

    def assert_order(self, order, payment_status, stock):
        order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual((order.payment_status, self.product.stock), (payment_status, stock))

    def test_open_session_is_expired_then_failed(self):
        order = self.order()
        self.retrieve.return_value = session("open")
        self.expire.return_value = session("expired")
        self.assertIn("failed=1", self.run_batch())
        self.expire.assert_called_once_with("cs_1")
        self.assert_order(order, "failed", 5)
        self.assertEqual(len(mail.outbox), 1)

    def test_expired_session(self):
        order = self.order()
        self.retrieve.return_value = session("expired")
        self.run_batch()
        self.expire.assert_not_called()
        self.assert_order(order, "failed", 5)

    def test_paid_session(self):
        order = self.order()
        self.retrieve.return_value = session("complete", "paid", "pi_1")
        self.assertIn("paid=1", self.run_batch())
        self.assert_order(order, "paid", 3)
        self.assertEqual(order.stripe_payment_intent_id, "pi_1")

    def test_konbini_waiting(self):
        order = self.order(payment_method="konbini")
        self.retrieve.return_value = session("complete", "unpaid", "pi_konbini")
        self.assertIn("waiting=1", self.run_batch())
        self.assert_order(order, "pending", 3)
        self.assertEqual(order.stripe_payment_intent_id, "pi_konbini")

    def test_without_session(self):
        order = self.order(session_id=None)
        self.run_batch()
        self.retrieve.assert_not_called()
        self.assert_order(order, "failed", 5)

    def test_stripe_error_is_retried_next_time(self):
        order = self.order()
        self.retrieve.side_effect = payments.PaymentError("down")
        with self.assertLogs("marche.management.commands.cancel_unpaid_orders", "ERROR"):
            self.assertIn("skipped=1", self.run_batch())
        self.assert_order(order, "pending", 3)

    def test_recent_and_paid_orders_are_left_alone(self):
        recent = self.order(minutes=10)
        paid = self.order()
        paid.payment_status = Order.PaymentStatus.PAID
        paid.save()
        self.run_batch()
        self.retrieve.assert_not_called()
        self.assert_order(recent, "pending", 3)
        self.assert_order(paid, "paid", 3)


class MarkOrderPaidCommandTests(TestCase):
    def setUp(self):
        self.order = make_order(user=make_user(), payment_status=Order.PaymentStatus.PENDING)
        add_shipment(self.order, make_producer())

    def test_only_in_debug(self):
        with self.assertRaises(CommandError):
            call_command("mark_order_paid", self.order.order_no, stdout=StringIO())
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, "pending")

    @override_settings(DEBUG=True)
    def test_marks_paid(self):
        with self.captureOnCommitCallbacks(execute=True):
            call_command("mark_order_paid", self.order.order_no, stdout=StringIO())
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, "paid")
        self.assertEqual(len(mail.outbox), 2)  # 購入者と生産者
        with self.assertRaises(CommandError):  # 2回目は pending ではない
            call_command("mark_order_paid", self.order.order_no, stdout=StringIO())
        with self.assertRaises(CommandError):
            call_command("mark_order_paid", "TM-00000000-000000", stdout=StringIO())


@override_settings(STRIPE_SECRET_KEY="sk_test_dummy", FRONTEND_BASE_URL="http://localhost:5173")
class CreateCheckoutSessionTests(TestCase):
    def test_params(self):
        order = make_order(user=make_user(), payment_status=Order.PaymentStatus.PENDING, payment_method="konbini")
        add_shipment(order, make_producer(), shipping_fee=800)
        fake = {"id": "cs_1", "url": "https://checkout.stripe.com/x", "expires_at": 1893456000}
        with patch("stripe.checkout.Session.create", return_value=fake) as create:
            result = payments.create_checkout_session(order, [("にんじん", 900, 2)], "buyer@example.com")
        self.assertEqual(result, fake)
        params = create.call_args.kwargs
        self.assertEqual(params["idempotency_key"], f"order-{order.id}-checkout")
        self.assertEqual(params["payment_method_types"], ["konbini"])
        self.assertEqual(params["payment_method_options"], {"konbini": {"expires_after_days": 3}})
        self.assertEqual([(li["price_data"]["product_data"]["name"], li["price_data"]["unit_amount"], li["quantity"])
                          for li in params["line_items"]], [("にんじん", 900, 2), ("送料", 800, 1)])
        self.assertEqual(params["metadata"]["order_id"], str(order.id))
        self.assertEqual(params["success_url"], f"http://localhost:5173/checkout/complete?orderId={order.id}")
        self.assertGreaterEqual(params["expires_at"] - int(timezone.now().timestamp()), 30 * 60)

    def test_stripe_error(self):
        import stripe
        order = make_order(user=make_user(), payment_status=Order.PaymentStatus.PENDING)
        with patch("stripe.checkout.Session.create", side_effect=stripe.APIConnectionError("down")), \
                self.assertLogs("api.services.payments", "ERROR"), self.assertRaises(payments.PaymentError):
            payments.create_checkout_session(order, [], "buyer@example.com")


class OrderNoTests(TestCase):
    def test_format_and_retry_on_duplicate(self):
        today = timezone.localdate().strftime("%Y%m%d")
        Order.objects.filter(pk=make_order(user=make_user()).pk).update(order_no=f"TM-{today}-000001")
        with patch("secrets.randbelow", side_effect=[1, 2]):
            self.assertEqual(orders.generate_order_no(), f"TM-{today}-000002")
