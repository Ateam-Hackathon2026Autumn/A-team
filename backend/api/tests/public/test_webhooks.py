"""Stripe の Webhook のテスト

テスト対象: api/views/public/webhooks.py（services/payments.py の parse_webhook、services/orders.py の
mark_paid・save_payment_intent・fail_order）
  - 決済結果の受信: POST /api/v1/webhooks/stripe
署名は Stripe と同じ方法（HMAC-SHA256）でテストの中で作り、本物の署名検証を通す。
"""
import hashlib
import hmac
import json
import re
import time
from types import SimpleNamespace

from django.core import mail
from django.test import override_settings

from marche.models import Notification, Order

from ...services.orders import hash_token
from ..utils import ApiTestCase, add_shipment, make_order, make_producer, make_product, make_user

URL = "/api/v1/webhooks/stripe"
SECRET = "whsec_test_secret"


def sign(payload, secret=SECRET, timestamp=None):
    timestamp = timestamp or int(time.time())
    signature = hmac.new(secret.encode(), f"{timestamp}.{payload}".encode(), hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={signature}"


@override_settings(STRIPE_WEBHOOK_SECRET=SECRET)
class WebhookTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.producer = make_producer(business_name="山田農園")
        self.product = make_product(self.producer, name="にんじん", price=1000, stock=3)
        self.unmanaged = make_product(self.producer, name="たまねぎ", price=500, stock=None)
        self.buyer = make_user(email="buyer@example.com", last_name="佐藤", first_name="花子")
        self.order = self.pending_order(user=self.buyer)

    def pending_order(self, **kw):
        order = make_order(payment_status=Order.PaymentStatus.PENDING, stripe_checkout_session_id="cs_1", **kw)
        add_shipment(order, self.producer, items=((self.product, 2), (self.unmanaged, 1)))
        return order

    def send(self, event_type, order=None, session_id="cs_1", payment_status="paid", payment_intent="pi_1",
             signature=None):
        order = order or self.order
        payload = json.dumps({
            "id": "evt_1", "object": "event", "type": event_type,
            "data": {"object": {
                "id": session_id, "object": "checkout.session", "status": "complete",
                "payment_status": payment_status, "payment_intent": payment_intent,
                "client_reference_id": str(order.id), "metadata": {"order_id": str(order.id)},
            }},
        })
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(URL, payload, content_type="application/json",
                                    HTTP_STRIPE_SIGNATURE=signature or sign(payload))

    def assert_status(self, payment_status, order=None):
        order = order or self.order
        order.refresh_from_db()
        self.assertEqual(order.payment_status, payment_status)

    def stocks(self):
        self.product.refresh_from_db()
        self.unmanaged.refresh_from_db()
        return self.product.stock, self.unmanaged.stock

    # ---- 署名 ----

    def test_invalid_signature(self):
        res = self.send("checkout.session.completed", signature=sign("{}", secret="whsec_other"))
        self.assertEqual((res.status_code, res.json()["errorCode"]), (400, "INVALID_SIGNATURE"))
        self.assert_status("pending")

    def test_missing_signature(self):
        res = self.client.post(URL, "{}", content_type="application/json")
        self.assertEqual(res.status_code, 400)

    def test_old_signature(self):
        payload = "{}"
        res = self.client.post(URL, payload, content_type="application/json",
                               HTTP_STRIPE_SIGNATURE=sign(payload, timestamp=int(time.time()) - 3600))
        self.assertEqual(res.status_code, 400)

    # ---- 支払い済み ----

    def test_completed_paid(self):
        res = self.send("checkout.session.completed")
        self.assertEqual((res.status_code, res.json()), (200, {"received": True}))
        self.assert_status("paid")
        self.assertEqual(self.order.stripe_payment_intent_id, "pi_1")
        self.assertEqual(self.stocks(), (3, None))  # 在庫は注文時に減らしてあるので、ここでは変えない
        self.assertEqual(sorted(m.to[0] for m in mail.outbox), ["buyer@example.com", self.producer.user.email])
        buyer_mail = next(m for m in mail.outbox if m.to == ["buyer@example.com"])
        self.assertIn(self.order.order_no, buyer_mail.subject)
        self.assertIn("にんじん × 2", buyer_mail.body)
        self.assertNotIn("#token=", buyer_mail.body)
        self.assertEqual(Notification.objects.filter(notification_type="new_order").count(), 2)

    def test_same_event_twice(self):
        self.send("checkout.session.completed")
        res = self.send("checkout.session.completed")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(mail.outbox), 2)  # 2回目は何もしない（購入者と生産者に1通ずつのまま）

    def test_guest_paid_gets_new_token(self):
        order = self.pending_order(guest_email="guest@example.com")
        order.stripe_checkout_session_id = "cs_guest"
        order.save()
        old_hash = order.access_token_hash
        self.send("checkout.session.completed", order=order, session_id="cs_guest")
        self.assert_status("paid", order)
        self.assertNotEqual(order.access_token_hash, old_hash)
        guest_mail = next(m for m in mail.outbox if m.to == ["guest@example.com"])
        token = re.search(rf"/orders/{order.id}#token=([A-Za-z0-9_-]+)", guest_mail.body).group(1)
        self.assertEqual(hash_token(token), order.access_token_hash)
        self.assertFalse(Notification.objects.filter(user__isnull=True).exists())

    def test_konbini_waiting_then_paid(self):
        self.send("checkout.session.completed", payment_status="unpaid", payment_intent="pi_konbini")
        self.assert_status("pending")
        self.assertEqual(self.order.stripe_payment_intent_id, "pi_konbini")
        self.assertEqual(mail.outbox, [])
        self.send("checkout.session.async_payment_succeeded", payment_intent="pi_konbini")
        self.assert_status("paid")

    # ---- 取り消し ----

    def test_expired(self):
        self.send("checkout.session.expired", payment_status="unpaid", payment_intent=None)
        self.assert_status("failed")
        self.assertEqual(self.stocks(), (5, None))  # 在庫管理しない商品はそのまま
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("期限が過ぎた", mail.outbox[0].body)
        self.assertEqual(Notification.objects.get().notification_type, "canceled")

    def test_async_payment_failed(self):
        self.send("checkout.session.async_payment_failed", payment_status="unpaid")
        self.assert_status("failed")
        self.assertEqual(self.stocks(), (5, None))
        self.assertIn("完了しなかった", mail.outbox[0].body)

    def test_expired_guest_mail_has_no_link_guide(self):
        order = self.pending_order(guest_email="guest@example.com")
        order.stripe_checkout_session_id = "cs_guest"
        order.save()
        self.send("checkout.session.expired", order=order, session_id="cs_guest", payment_status="unpaid")
        self.assertEqual(mail.outbox[0].to, ["guest@example.com"])
        self.assertNotIn("注文確認メールのURL", mail.outbox[0].body)

    def test_expired_after_paid_does_nothing(self):
        self.send("checkout.session.completed")
        self.send("checkout.session.expired")
        self.assert_status("paid")
        self.assertEqual(self.stocks(), (3, None))

    # ---- 対象外 ----

    def test_session_id_mismatch_is_ignored(self):
        with self.assertLogs("api.views.public.webhooks", "WARNING"):
            res = self.send("checkout.session.completed", session_id="cs_other")
        self.assertEqual(res.status_code, 200)
        self.assert_status("pending")

    def test_unknown_order_is_ignored(self):
        with self.assertLogs("api.views.public.webhooks", "WARNING"):
            res = self.send("checkout.session.completed", order=SimpleNamespace(id=self.order.id + 100))
        self.assertEqual(res.status_code, 200)

    def test_other_event_is_ignored(self):
        res = self.send("payment_intent.created")
        self.assertEqual(res.status_code, 200)
        self.assert_status("pending")
