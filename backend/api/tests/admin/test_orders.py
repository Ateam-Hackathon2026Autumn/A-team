"""注文・返金管理（管理者） のテスト

テスト対象: api/views/admin/orders.py
  - 注文一覧: GET /api/v1/admin/orders
  - 注文詳細: GET /api/v1/admin/orders/:orderId
  - 注文キャンセル: POST /api/v1/admin/orders/:orderId/cancel
  - 返金: POST /api/v1/admin/orders/:orderId/refund
S3 には接続しない（ApiTestCase）。メールは locmem（django.core.mail.outbox）で確認する。
"""
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import Group
from django.core import mail
from django.test import override_settings
from django.utils import timezone

from marche.models import AuditLog, Inquiry, Notification, Order, OrderShipment, Product

from ...services.payments import PaymentError
from ..utils import ApiTestCase, add_shipment, make_order, make_producer, make_product, make_user

Status = OrderShipment.Status
LIST_URL = "/api/v1/admin/orders"


def detail_url(order_id):
    return f"/api/v1/admin/orders/{order_id}"


def cancel_url(order_id):
    return f"/api/v1/admin/orders/{order_id}/cancel"


def refund_url(order_id):
    return f"/api/v1/admin/orders/{order_id}/refund"


def make_staff(email, *groups):
    staff = make_user(email=email, is_staff=True, last_name="運営", first_name="花子")
    for name in groups:
        staff.groups.add(Group.objects.get_or_create(name=name)[0])
    return staff


class AdminOrderTestCase(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.staff = make_staff("cs@example.com", "CS")
        self.producer = make_producer(business_name="山田農園")
        self.other = make_producer(business_name="佐藤漁港")
        self.buyer = make_user(email="buyer@example.com", last_name="鈴木", first_name="一郎", phone="09011112222")
        self.signin("cs@example.com")


# =========================================================
# 権限
# =========================================================

class PermissionTests(AdminOrderTestCase):
    def test_groups(self):
        self.post_json("/api/v1/auth/signout")
        self.assertEqual(self.client.get(LIST_URL).status_code, 401)

        cases = [
            (make_user(email="member@example.com"), 403),                    # 運営スタッフでない
            (make_staff("staff@example.com"), 403),                          # グループなし
            (make_staff("reviewer@example.com", "審査担当"), 403),            # 審査担当は注文を扱えない
            (make_staff("admin@example.com", "管理者"), 200),                 # 管理者はすべて
            (make_staff("cs2@example.com", "CS"), 200),
        ]
        for user, expected in cases:
            with self.subTest(email=user.email):
                self.signin(user.email)
                self.assertEqual(self.client.get(LIST_URL).status_code, expected)
                self.post_json("/api/v1/auth/signout")


# =========================================================
# 注文一覧・詳細
# =========================================================

class OrderListTests(AdminOrderTestCase):
    def test_item_shape_member_and_guest(self):
        member = make_order(user=self.buyer)
        add_shipment(member, self.producer)
        guest = make_order(guest_email="guest@example.com")
        add_shipment(guest, self.other)
        Order.objects.filter(pk=member.pk).update(ordered_at=timezone.now() - timedelta(hours=1))

        res = self.client.get(LIST_URL)
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual((body["total"], body["totalPages"]), (2, 1))
        guest_item, member_item = body["items"]
        self.assertEqual(member_item["orderId"], member.id)
        self.assertEqual(member_item["buyer"], {"type": "member", "userId": self.buyer.id, "name": "鈴木 一郎",
                                                "email": "buyer@example.com"})
        self.assertEqual(guest_item["buyer"], {"type": "guest", "userId": None, "name": "佐藤 花子",
                                               "email": "guest@example.com"})
        self.assertEqual(member_item["shipments"][0]["producerName"], "山田農園")
        self.assertEqual(member_item["grandTotal"], 2000)

    def test_filters(self):
        paid = make_order(user=self.buyer)
        add_shipment(paid, self.producer, status=Status.SHIPPED)
        pending = make_order(guest_email="other@example.com", payment_status=Order.PaymentStatus.PENDING)
        add_shipment(pending, self.producer)
        refund_waiting = make_order(user=self.buyer)
        add_shipment(refund_waiting, self.producer, status=Status.CANCELED)
        refunded = make_order(user=self.buyer)
        add_shipment(refunded, self.producer, status=Status.CANCELED, refunded_amount=2000)
        Order.objects.filter(pk=paid.pk).update(ordered_at=timezone.now() - timedelta(days=10))

        def ids(**params):
            return sorted(item["orderId"] for item in self.client.get(LIST_URL, params).json()["items"])

        self.assertEqual(ids(keyword=paid.order_no), [paid.id])
        self.assertEqual(ids(keyword="other@"), [pending.id])
        self.assertEqual(ids(keyword="BUYER@example"), sorted([paid.id, refund_waiting.id, refunded.id]))
        self.assertEqual(ids(paymentStatus="pending"), [pending.id])
        self.assertEqual(ids(shipmentStatus="shipped"), [paid.id])
        self.assertEqual(ids(refundPending="true"), [refund_waiting.id])
        today = timezone.localdate().isoformat()
        self.assertNotIn(paid.id, ids(startDate=today))
        self.assertEqual(ids(endDate=(timezone.localdate() - timedelta(days=5)).isoformat()), [paid.id])

    def test_invalid_query_is_400(self):
        bad = ["?startDate=abc", "?startDate=2026-11-10&endDate=2026-11-01", "?paymentStatus=done",
               "?refundPending=maybe", "?foo=1", "?pageSize=abc", "?page=1&page=2"]
        for query in bad:
            with self.subTest(query=query):
                res = self.client.get(LIST_URL + query)
                self.assertEqual((res.status_code, res.json()["errorCode"]), (400, "VALIDATION_ERROR"))

    def test_query_count_does_not_grow(self):
        for _ in range(5):
            order = make_order(user=self.buyer)
            add_shipment(order, self.producer)
            add_shipment(order, self.other, temperature_zone="frozen")
        # セッション・ユーザー・グループ・件数・注文（会員を JOIN）・箱（生産者を JOIN）・明細＋SAVEPOINT・RELEASE
        with self.assertNumQueries(9):
            self.client.get(LIST_URL)


class OrderDetailTests(AdminOrderTestCase):
    def test_detail(self):
        order = make_order(user=self.buyer, stripe_payment_intent_id="pi_123")
        add_shipment(order, self.producer)
        Inquiry.objects.create(user=self.buyer, order=order, email="buyer@example.com", category="order",
                               subject="届きません", body="まだ届きません", status="open", priority="medium")
        AuditLog.objects.create(admin=self.staff, action="cancel", target_type="order", target_id=order.id,
                                detail={"reason": "テスト"})
        AuditLog.objects.create(admin=self.staff, action="cancel", target_type="order", target_id=order.id + 1)

        res = self.client.get(detail_url(order.id))
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["buyer"]["phone"], "09011112222")
        self.assertEqual(body["stripePaymentIntentId"], "pi_123")
        self.assertEqual(body["shipName"], "佐藤 花子")
        self.assertEqual([inquiry["subject"] for inquiry in body["inquiries"]], ["届きません"])
        self.assertEqual(len(body["operationHistory"]), 1)
        self.assertEqual(body["operationHistory"][0]["adminName"], "運営 花子")

    def test_guest_phone_and_404(self):
        order = make_order(guest_email="guest@example.com")
        add_shipment(order, self.producer)
        self.assertEqual(self.client.get(detail_url(order.id)).json()["buyer"]["phone"], "09012345678")
        self.assertEqual(self.client.get(detail_url(999999)).status_code, 404)


# =========================================================
# 注文キャンセル
# =========================================================

class CancelTests(AdminOrderTestCase):
    def test_cancel_boxes_restores_stock_only_for_unshipped(self):
        product = make_product(self.producer, stock=5)
        fish = make_product(self.other, name="干物", stock=5)
        order = make_order(user=self.buyer)
        unshipped = add_shipment(order, self.producer, items=((product, 2),))
        shipped = add_shipment(order, self.other, items=((fish, 1),), status=Status.SHIPPED)
        untouched = add_shipment(order, self.producer, temperature_zone="frozen")

        with self.captureOnCommitCallbacks(execute=True):
            res = self.post_json(cancel_url(order.id), {"shipmentIds": [unshipped.id, shipped.id],
                                                        "reason": "購入者から連絡がありました"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual([shipment["id"] for shipment in res.json()["shipments"]], [unshipped.id, shipped.id])
        for shipment in (unshipped, shipped):
            shipment.refresh_from_db()
            self.assertEqual((shipment.status, shipment.cancel_reason), (Status.CANCELED, "購入者から連絡がありました"))
            self.assertIsNone(shipment.refunded_amount)  # 返金待ち
        untouched.refresh_from_db()
        self.assertEqual(untouched.status, Status.UNSHIPPED)
        self.assertEqual(Product.objects.get(pk=product.pk).stock, 7)  # 未発送だった箱は戻す
        self.assertEqual(Product.objects.get(pk=fish.pk).stock, 5)  # 発送済みの箱は戻さない

        log = AuditLog.objects.get()
        self.assertEqual((log.admin, log.action, log.target_type, log.target_id), (self.staff, "cancel", "order", order.id))
        self.assertEqual(log.detail["shipments"], [{"shipment_id": unshipped.id, "previous_status": "unshipped"},
                                                   {"shipment_id": shipped.id, "previous_status": "shipped"}])
        # 購入者1通＋生産者2人
        self.assertEqual(sorted(n.user_id for n in Notification.objects.all()),
                         sorted([self.buyer.id, self.producer.user_id, self.other.user_id]))
        self.assertEqual(len(mail.outbox), 3)

    def test_errors(self):
        order = make_order(user=self.buyer)
        canceled = add_shipment(order, self.producer, status=Status.CANCELED)
        other_order = make_order(user=self.buyer)
        other_box = add_shipment(other_order, self.producer)
        pending = make_order(user=self.buyer, payment_status=Order.PaymentStatus.PENDING)
        pending_box = add_shipment(pending, self.producer)

        res = self.post_json(cancel_url(order.id), {"shipmentIds": [canceled.id], "reason": "x"})
        self.assertEqual((res.status_code, res.json()["errorCode"]), (409, "SHIPMENT_STATE_CONFLICT"))
        res = self.post_json(cancel_url(pending.id), {"shipmentIds": [pending_box.id], "reason": "x"})
        self.assertEqual((res.status_code, res.json()["errorCode"]), (409, "SHIPMENT_STATE_CONFLICT"))
        res = self.post_json(cancel_url(order.id), {"shipmentIds": [other_box.id], "reason": "x"})
        self.assertEqual(res.status_code, 404)
        for data in [{"shipmentIds": [], "reason": "x"}, {"shipmentIds": [1, 1], "reason": "x"},
                     {"shipmentIds": [canceled.id]}, {"shipmentIds": [canceled.id], "reason": ""}]:
            with self.subTest(data=data):
                self.assertEqual(self.post_json(cancel_url(order.id), data).status_code, 400)
        self.assertEqual(AuditLog.objects.count(), 0)


# =========================================================
# 返金
# =========================================================

class RefundTests(AdminOrderTestCase):
    def setUp(self):
        super().setUp()
        self.order = make_order(user=self.buyer, payment_method="konbini")
        self.box = add_shipment(self.order, self.producer, items=((None, 2),), status=Status.CANCELED,
                                shipping_fee=1200)

    def test_manual_refund_records_full_amount(self):
        res = self.post_json(refund_url(self.order.id), {"shipmentId": self.box.id, "method": "manual"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["refundedAmount"], 3200)  # 1000円×2＋送料1200円（数値）
        self.box.refresh_from_db()
        self.assertEqual(self.box.refunded_amount, 3200)
        log = AuditLog.objects.get()
        self.assertEqual((log.action, log.detail), ("refund", {"shipment_id": self.box.id, "method": "manual",
                                                               "refunded_amount": 3200}))

    def test_manual_refund_notifies_buyer(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.post_json(refund_url(self.order.id), {"shipmentId": self.box.id, "method": "manual"})
        self.assertEqual(Notification.objects.get(user=self.buyer).title, "返金が完了しました")
        self.assertIn("3,200円を返金しました", mail.outbox[0].body)
        self.assertNotIn("ご利用明細", mail.outbox[0].body)

    @override_settings(STRIPE_SECRET_KEY="sk_test_dummy")
    def test_konbini_cannot_use_stripe(self):
        res = self.post_json(refund_url(self.order.id), {"shipmentId": self.box.id, "method": "stripe"})
        self.assertEqual((res.status_code, res.json()["errorCode"]), (409, "STRIPE_REFUND_NOT_AVAILABLE"))
        self.assertEqual(res.json()["errorMsg"], "コンビニ払いは Stripe で返金できません。")
        self.box.refresh_from_db()
        self.assertIsNone(self.box.refunded_amount)
        self.assertFalse(AuditLog.objects.exists())

    def test_not_waiting_for_refund_is_409(self):
        self.post_json(refund_url(self.order.id), {"shipmentId": self.box.id, "method": "manual"})
        res = self.post_json(refund_url(self.order.id), {"shipmentId": self.box.id, "method": "manual"})
        self.assertEqual((res.status_code, res.json()["errorCode"]), (409, "SHIPMENT_STATE_CONFLICT"))
        unshipped = add_shipment(self.order, self.other)
        res = self.post_json(refund_url(self.order.id), {"shipmentId": unshipped.id, "method": "manual"})
        self.assertEqual(res.status_code, 409)

    def test_other_orders_box_is_404_and_bad_method_is_400(self):
        other_order = make_order(user=self.buyer)
        res = self.post_json(refund_url(other_order.id), {"shipmentId": self.box.id, "method": "manual"})
        self.assertEqual(res.status_code, 404)
        res = self.post_json(refund_url(self.order.id), {"shipmentId": self.box.id, "method": "cash"})
        self.assertEqual(res.status_code, 400)


@override_settings(STRIPE_SECRET_KEY="sk_test_dummy")
class StripeRefundTests(AdminOrderTestCase):
    """カード払いの箱の Stripe 返金（管理者返金 method=stripe・管理者キャンセル）"""

    def setUp(self):
        super().setUp()
        self.order = make_order(user=self.buyer, stripe_payment_intent_id="pi_1")
        self.box = add_shipment(self.order, self.producer, items=((None, 2),), status=Status.CANCELED,
                                shipping_fee=1200)
        self.refund = patch("api.services.payments.refund_shipment").start()
        self.addCleanup(patch.stopall)

    def stripe_refund(self):
        return self.post_json(refund_url(self.order.id), {"shipmentId": self.box.id, "method": "stripe"})

    def test_refund(self):
        self.refund.return_value = {"id": "re_1", "status": "succeeded", "amount": 3200}
        with self.captureOnCommitCallbacks(execute=True):
            res = self.stripe_refund()
        self.assertEqual(res.status_code, 200)
        self.assertEqual((res.json()["refundedAmount"], res.json()["stripeRefundId"]), (3200, "re_1"))
        self.refund.assert_called_once_with("pi_1", self.box.id, 3200)
        self.assertEqual(AuditLog.objects.get().detail, {"shipment_id": self.box.id, "method": "stripe",
                                                         "refunded_amount": 3200, "stripe_refund_id": "re_1"})
        self.assertIn("ご利用明細", mail.outbox[0].body)

    def test_stripe_error_is_502(self):
        self.refund.side_effect = PaymentError("down")
        res = self.stripe_refund()
        self.assertEqual((res.status_code, res.json()["errorCode"]), (502, "STRIPE_ERROR"))
        self.box.refresh_from_db()
        self.assertIsNone(self.box.refunded_amount)
        self.assertFalse(AuditLog.objects.exists())

    @override_settings(STRIPE_SECRET_KEY="")
    def test_without_key_is_409(self):
        res = self.stripe_refund()
        self.assertEqual((res.status_code, res.json()["errorCode"]), (409, "STRIPE_REFUND_NOT_AVAILABLE"))
        self.refund.assert_not_called()

    def test_without_payment_intent_is_409(self):
        Order.objects.filter(pk=self.order.pk).update(stripe_payment_intent_id=None)
        res = self.stripe_refund()
        self.assertEqual((res.status_code, res.json()["errorCode"]), (409, "STRIPE_REFUND_NOT_AVAILABLE"))

    def test_admin_cancel_refunds_card_boxes(self):
        self.refund.return_value = {"id": "re_2", "status": "succeeded", "amount": 1000}
        box = add_shipment(self.order, self.other, items=((None, 1),), shipping_fee=0)
        res = self.post_json(cancel_url(self.order.id), {"shipmentIds": [box.id], "reason": "生産者の都合"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["shipments"][0]["refundedAmount"], 1000)
        box.refresh_from_db()
        self.assertEqual((box.status, box.stripe_refund_id), (Status.CANCELED, "re_2"))
