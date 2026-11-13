"""注文・配送・キャンセル承認（生産者） のテスト

テスト対象: api/views/dashboard/orders.py
  - 注文一覧: GET /api/v1/dashboard/orders
  - 注文詳細: GET /api/v1/dashboard/orders/:orderId
  - 配送状況更新: PATCH /api/v1/dashboard/orders/:orderId/shipping
  - キャンセル承認・拒否: POST /api/v1/dashboard/orders/:orderId/cancel/approve・reject
S3 には接続しない（ApiTestCase）。メールは locmem（django.core.mail.outbox）で確認する。
"""
from datetime import timedelta
from unittest.mock import patch

from django.core import mail
from django.test import override_settings
from django.utils import timezone

from marche.models import Notification, Order, OrderShipment, Producer, Product, PublishStatus

from ...services.payments import PaymentError
from ..utils import ApiTestCase, add_shipment, make_order, make_producer, make_product, make_user

Status = OrderShipment.Status
LIST_URL = "/api/v1/dashboard/orders"


def detail_url(order_id):
    return f"/api/v1/dashboard/orders/{order_id}"


def shipping_url(order_id):
    return f"/api/v1/dashboard/orders/{order_id}/shipping"


def approve_url(order_id):
    return f"/api/v1/dashboard/orders/{order_id}/cancel/approve"


def reject_url(order_id):
    return f"/api/v1/dashboard/orders/{order_id}/cancel/reject"


class DashboardOrderTestCase(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.producer = make_producer(business_name="山田農園")
        self.other = make_producer(business_name="佐藤漁港")
        self.buyer = make_user(email="buyer@example.com", last_name="鈴木", first_name="一郎")
        self.signin(self.producer.user.email)

    def order_with_boxes(self, status=Status.UNSHIPPED, **kw):
        """自分の箱1つ（明細2つ）と、他の生産者の箱1つがある注文"""
        order = make_order(user=self.buyer, **kw)
        mine = add_shipment(order, self.producer, items=((None, 2), (None, 1)), status=status)
        add_shipment(order, self.other, temperature_zone="frozen", shipping_fee=1500)
        return order, mine


# =========================================================
# 権限
# =========================================================

class PermissionTests(DashboardOrderTestCase):
    def test_not_signed_in_is_401(self):
        self.post_json("/api/v1/auth/signout")
        res = self.client.get(LIST_URL)
        self.assertEqual((res.status_code, res.json()["errorCode"]), (401, "NOT_AUTHENTICATED"))

    def test_not_approved_producer_is_403(self):
        pending = make_producer(approval=Producer.ApprovalStatus.PENDING)
        self.post_json("/api/v1/auth/signout")
        self.signin(pending.user.email)
        self.assertEqual(self.client.get(LIST_URL).status_code, 403)

    def test_suspended_producer_can_still_ship(self):
        self.producer.publish_status = PublishStatus.SUSPENDED
        self.producer.save()
        order, mine = self.order_with_boxes()
        res = self.patch_json(shipping_url(order.id), {"shipmentId": mine.id, "status": "shipped"})
        self.assertEqual(res.status_code, 200)


# =========================================================
# 注文一覧・詳細
# =========================================================

class OrderListTests(DashboardOrderTestCase):
    def test_only_my_paid_orders_with_my_boxes(self):
        order, mine = self.order_with_boxes()
        make_order(user=self.buyer, payment_status=Order.PaymentStatus.PENDING)  # 箱なし
        pending = make_order(user=self.buyer, payment_status=Order.PaymentStatus.PENDING)
        add_shipment(pending, self.producer)
        others_only = make_order(user=self.buyer)
        add_shipment(others_only, self.other)

        res = self.client.get(LIST_URL)
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual((body["total"], body["page"], body["pageSize"], body["totalPages"]), (1, 1, 20, 1))
        item = body["items"][0]
        self.assertEqual(set(item), {"orderId", "orderNo", "orderedAt", "paymentStatus", "producerItemsTotal",
                                     "producerShippingTotal", "producerTotal", "shipments"})
        self.assertEqual(item["orderId"], order.id)
        self.assertEqual([shipment["id"] for shipment in item["shipments"]], [mine.id])  # 他の生産者の箱は返さない
        self.assertEqual((item["producerItemsTotal"], item["producerShippingTotal"], item["producerTotal"]),
                         (3000, 1000, 4000))
        shipment = item["shipments"][0]
        self.assertNotIn("etag", shipment)
        self.assertEqual(len(shipment["items"]), 2)
        self.assertEqual(set(shipment["items"][0]), {"id", "productId", "productName", "unitPrice", "discountRate",
                                                     "paidUnitPrice", "quantity", "taxRate", "subtotal"})

    def test_newest_first_and_shipment_status_filter(self):
        old, _ = self.order_with_boxes()
        Order.objects.filter(pk=old.pk).update(ordered_at=timezone.now() - timedelta(days=1))
        new, _ = self.order_with_boxes(status=Status.SHIPPED)
        self.assertEqual([item["orderId"] for item in self.client.get(LIST_URL).json()["items"]], [new.id, old.id])
        res = self.client.get(LIST_URL, {"shipmentStatus": "shipped"})
        self.assertEqual([item["orderId"] for item in res.json()["items"]], [new.id])
        # 他の生産者の箱の状態では絞り込まない
        self.assertEqual(self.client.get(LIST_URL, {"shipmentStatus": "canceled"}).json()["total"], 0)

    def test_invalid_query_is_400(self):
        for query in ["?paymentStatus=paid", "?shipmentStatus=lost", "?pageSize=101", "?page=0", "?foo=1"]:
            with self.subTest(query=query):
                self.assertEqual(self.client.get(LIST_URL + query).status_code, 400)

    def test_query_count_does_not_grow(self):
        for _ in range(5):
            self.order_with_boxes()
        # セッション・ユーザー・生産者・件数・注文・箱・明細＋SAVEPOINT・RELEASE
        with self.assertNumQueries(9):
            self.client.get(LIST_URL)


class OrderDetailTests(DashboardOrderTestCase):
    def test_detail_has_address_but_no_buyer_account(self):
        order, mine = self.order_with_boxes()
        res = self.client.get(detail_url(order.id))
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["shippingAddress"], {
            "name": "佐藤 花子", "postalCode": "1000001", "prefecture": "東京都", "city": "千代田区",
            "addressLine1": "千代田1-1", "addressLine2": None, "phone": "0312345678"})
        self.assertEqual([shipment["id"] for shipment in body["shipments"]], [mine.id])
        self.assertNotIn("buyer@example.com", res.content.decode())

    def test_not_mine_or_unpaid_is_404(self):
        others = make_order(user=self.buyer)
        add_shipment(others, self.other)
        pending = make_order(user=self.buyer, payment_status=Order.PaymentStatus.PENDING)
        add_shipment(pending, self.producer)
        for order_id in [others.id, pending.id, 999999]:
            res = self.client.get(detail_url(order_id))
            self.assertEqual((res.status_code, res.json()["errorCode"]), (404, "NOT_FOUND"))


# =========================================================
# 配送状況更新
# =========================================================

class ShippingTests(DashboardOrderTestCase):
    def test_ship_with_tracking_number(self):
        order, mine = self.order_with_boxes()
        with self.captureOnCommitCallbacks(execute=True):  # メールはコミット後に送る
            res = self.patch_json(shipping_url(order.id),
                                  {"shipmentId": mine.id, "status": "shipped", "trackingNo": "1234-5678"})
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual((body["id"], body["status"], body["trackingNo"]), (mine.id, "shipped", "1234-5678"))
        self.assertIsNotNone(body["shippedAt"])
        mine.refresh_from_db()
        self.assertEqual(mine.status, Status.SHIPPED)
        notification = Notification.objects.get(user=self.buyer)
        self.assertEqual(notification.notification_type, Notification.NotificationType.SHIPPED)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("1234-5678", mail.outbox[0].body)

    def test_ship_without_tracking_number_and_guest_gets_mail_only(self):
        order = make_order(guest_email="guest@example.com")
        mine = add_shipment(order, self.producer)
        with self.captureOnCommitCallbacks(execute=True):
            res = self.patch_json(shipping_url(order.id), {"shipmentId": mine.id, "status": "shipped"})
        self.assertEqual((res.status_code, res.json()["trackingNo"]), (200, None))
        self.assertEqual(Notification.objects.count(), 0)
        self.assertEqual(mail.outbox[0].to, ["guest@example.com"])
        self.assertIn("注文確認メールのURL", mail.outbox[0].body)

    def test_deliver_after_ship(self):
        order, mine = self.order_with_boxes(status=Status.SHIPPED)
        with self.captureOnCommitCallbacks(execute=True):
            res = self.patch_json(shipping_url(order.id), {"shipmentId": mine.id, "status": "delivered"})
        self.assertEqual((res.status_code, res.json()["status"]), (200, "delivered"))
        self.assertEqual(len(mail.outbox), 0)  # 配達完了は通知しない

    def test_wrong_state_is_409(self):
        cases = [
            (Status.SHIPPED, "shipped"), (Status.UNSHIPPED, "delivered"), (Status.CANCEL_REQUESTED, "shipped"),
            (Status.CANCELED, "shipped"), (Status.DELIVERED, "delivered"),
        ]
        for current, requested in cases:
            with self.subTest(current=current, requested=requested):
                order, mine = self.order_with_boxes(status=current)
                res = self.patch_json(shipping_url(order.id), {"shipmentId": mine.id, "status": requested})
                self.assertEqual((res.status_code, res.json()["errorCode"]), (409, "SHIPMENT_STATE_CONFLICT"))

    def test_unpaid_order_cannot_be_shipped(self):
        order, mine = self.order_with_boxes(payment_status=Order.PaymentStatus.PENDING)
        res = self.patch_json(shipping_url(order.id), {"shipmentId": mine.id, "status": "shipped"})
        self.assertEqual((res.status_code, res.json()["errorCode"]), (409, "SHIPMENT_STATE_CONFLICT"))
        mine.refresh_from_db()
        self.assertEqual(mine.status, Status.UNSHIPPED)

    def test_other_producers_box_or_other_order_is_404(self):
        order, mine = self.order_with_boxes()
        others_box = order.order_shipments.get(producer=self.other)
        another_order, _ = self.order_with_boxes()
        for order_id, shipment_id in [(order.id, others_box.id), (another_order.id, mine.id), (999999, mine.id)]:
            res = self.patch_json(shipping_url(order_id), {"shipmentId": shipment_id, "status": "shipped"})
            self.assertEqual(res.status_code, 404)

    def test_invalid_body_is_400(self):
        order, mine = self.order_with_boxes(status=Status.SHIPPED)
        bad = [
            {"shipmentId": mine.id},
            {"shipmentId": mine.id, "status": "canceled"},
            {"shipmentId": mine.id, "status": "delivered", "trackingNo": "1"},
            {"shipmentId": mine.id, "status": "shipped", "trackingNo": "x" * 31},
            {"shipmentId": mine.id, "status": "shipped", "foo": 1},
        ]
        for data in bad:
            with self.subTest(data=data):
                self.assertEqual(self.patch_json(shipping_url(order.id), data).status_code, 400)


# =========================================================
# キャンセル承認・拒否
# =========================================================

class CancelApproveRejectTests(DashboardOrderTestCase):
    def test_approve_cancels_my_requested_boxes_and_restores_stock(self):
        managed = make_product(self.producer, name="在庫あり", stock=3)
        unmanaged = make_product(self.producer, name="在庫管理なし", stock=None)
        order = make_order(user=self.buyer)
        requested = add_shipment(order, self.producer, items=((managed, 2), (unmanaged, 1)),
                                 status=Status.CANCEL_REQUESTED, cancel_reason="間違えて注文しました")
        frozen = add_shipment(order, self.producer, temperature_zone="frozen", status=Status.CANCEL_REQUESTED)
        others = add_shipment(order, self.other, status=Status.CANCEL_REQUESTED)

        res = self.post_json(approve_url(order.id))
        self.assertEqual(res.status_code, 200)
        self.assertEqual([shipment["id"] for shipment in res.json()["shipments"]], [requested.id, frozen.id])
        for shipment in (requested, frozen):
            shipment.refresh_from_db()
            self.assertEqual(shipment.status, Status.CANCELED)
            self.assertIsNotNone(shipment.canceled_at)
            self.assertIsNone(shipment.refunded_amount)  # 返金待ち
        others.refresh_from_db()
        self.assertEqual(others.status, Status.CANCEL_REQUESTED)  # 他の生産者の箱はそのまま
        self.assertEqual(Product.objects.get(pk=managed.pk).stock, 5)
        self.assertIsNone(Product.objects.get(pk=unmanaged.pk).stock)
        self.assertEqual(Notification.objects.get(user=self.buyer).notification_type,
                         Notification.NotificationType.CANCELED)

    def test_reject_returns_to_unshipped(self):
        order, mine = self.order_with_boxes(status=Status.CANCEL_REQUESTED)
        with self.captureOnCommitCallbacks(execute=True):
            res = self.post_json(reject_url(order.id))
        self.assertEqual((res.status_code, res.json()["shipments"][0]["status"]), (200, "unshipped"))
        mine.refresh_from_db()
        self.assertEqual(mine.status, Status.UNSHIPPED)
        self.assertEqual(Notification.objects.get(user=self.buyer).notification_type,
                         Notification.NotificationType.CANCEL_REJECTED)
        self.assertEqual(mail.outbox[0].to, ["buyer@example.com"])

    def test_nothing_to_approve_is_409(self):
        order, _ = self.order_with_boxes(status=Status.UNSHIPPED)
        for url in [approve_url(order.id), reject_url(order.id)]:
            res = self.post_json(url)
            self.assertEqual((res.status_code, res.json()["errorCode"]), (409, "SHIPMENT_STATE_CONFLICT"))

    def test_not_my_order_is_404_and_body_is_rejected(self):
        others = make_order(user=self.buyer)
        add_shipment(others, self.other, status=Status.CANCEL_REQUESTED)
        self.assertEqual(self.post_json(approve_url(others.id)).status_code, 404)
        order, _ = self.order_with_boxes(status=Status.CANCEL_REQUESTED)
        self.assertEqual(self.post_json(approve_url(order.id), {"reason": "x"}).status_code, 400)

    def test_csrf_is_required(self):
        order, _ = self.order_with_boxes(status=Status.CANCEL_REQUESTED)
        res = self.post_json(approve_url(order.id), csrf=False)
        self.assertEqual((res.status_code, res.json()["errorCode"]), (403, "CSRF_FAILED"))


@override_settings(STRIPE_SECRET_KEY="sk_test_dummy")
class ApproveStripeRefundTests(DashboardOrderTestCase):
    """キャンセル承認のあと、カード払いの箱を Stripe で返金する"""

    def setUp(self):
        super().setUp()
        self.order = make_order(user=self.buyer, stripe_payment_intent_id="pi_1")
        self.box = add_shipment(self.order, self.producer, items=((None, 2),), shipping_fee=800,
                                status=Status.CANCEL_REQUESTED)
        self.refund = patch("api.services.payments.refund_shipment").start()
        self.addCleanup(patch.stopall)

    def test_card_is_refunded(self):
        self.refund.return_value = {"id": "re_1", "status": "succeeded", "amount": 2800}
        with self.captureOnCommitCallbacks(execute=True):
            res = self.post_json(approve_url(self.order.id))
        self.assertEqual((res.status_code, res.json()["shipments"][0]["refundedAmount"]), (200, 2800))
        self.refund.assert_called_once_with("pi_1", self.box.id, 2800)  # 1,000円×2＋送料800円
        self.box.refresh_from_db()
        self.assertEqual((self.box.refunded_amount, self.box.stripe_refund_id), (2800, "re_1"))
        self.assertEqual([n.title for n in Notification.objects.filter(user=self.buyer).order_by("id")],
                         ["キャンセルが確定しました", "返金が完了しました"])
        self.assertIn("2,800円を返金しました", mail.outbox[-1].body)

    def test_stripe_error_keeps_waiting(self):
        self.refund.side_effect = PaymentError("down")
        with self.assertLogs("api.services.orders", "ERROR"):
            res = self.post_json(approve_url(self.order.id))
        self.assertEqual(res.status_code, 200)
        self.assertIsNone(res.json()["shipments"][0]["refundedAmount"])
        self.box.refresh_from_db()
        self.assertEqual((self.box.status, self.box.refunded_amount), (Status.CANCELED, None))

    def test_pending_refund_is_recorded(self):
        self.refund.return_value = {"id": "re_1", "status": "pending", "amount": 2800}
        self.post_json(approve_url(self.order.id))
        self.box.refresh_from_db()
        self.assertEqual(self.box.refunded_amount, 2800)

    def test_failed_refund_is_not_recorded(self):
        self.refund.return_value = {"id": "re_1", "status": "failed", "amount": 2800}
        with self.assertLogs("api.services.orders", "ERROR"):
            self.post_json(approve_url(self.order.id))
        self.box.refresh_from_db()
        self.assertIsNone(self.box.refunded_amount)

    def test_konbini_and_no_key_are_not_sent_to_stripe(self):
        Order.objects.filter(pk=self.order.pk).update(payment_method="konbini")
        self.post_json(approve_url(self.order.id))
        konbini_order = make_order(user=self.buyer, stripe_payment_intent_id="pi_2")
        add_shipment(konbini_order, self.producer, status=Status.CANCEL_REQUESTED)
        with override_settings(STRIPE_SECRET_KEY=""):
            self.post_json(approve_url(konbini_order.id))
        self.refund.assert_not_called()
        self.assertFalse(OrderShipment.objects.filter(refunded_amount__isnull=False).exists())
