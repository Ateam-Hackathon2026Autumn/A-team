"""売上 のテスト

テスト対象: api/views/dashboard/sales.py
  - 売上: GET /api/v1/dashboard/sales
      ・発送済みの箱を shipped_at の日本時間の月で集計。入金予定は未発送・キャンセル申請中。month を付けると箱の一覧
"""
from datetime import datetime

from django.utils import timezone

from marche.models import Order, OrderShipment

from ..utils import ApiTestCase, add_shipment, make_order, make_producer, make_product, make_user

URL = "/api/v1/dashboard/sales"


def jst(*args):
    return timezone.make_aware(datetime(*args))


class SalesTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.producer = make_producer()
        self.product = make_product(self.producer)  # 1,000円
        self.buyer = make_user(email="buyer@example.com")
        self.signin(self.producer.user.email)

    def shipped(self, at, quantity=1, status=OrderShipment.Status.SHIPPED, producer=None, **kw):
        producer = producer or self.producer
        product = self.product if producer == self.producer else make_product(producer)
        return add_shipment(make_order(user=self.buyer, **kw), producer, items=((product, quantity),),
                            status=status, shipped_at=at)

    def test_monthly(self):
        self.shipped(jst(2026, 1, 1, 0, 30), quantity=2)                   # 日本時間で1月（UTC では前の年）
        self.shipped(jst(2026, 1, 31, 23, 59), status=OrderShipment.Status.DELIVERED)
        self.shipped(jst(2026, 11, 5, 10))
        self.shipped(jst(2025, 12, 31, 23, 59))                            # 前の年
        self.shipped(jst(2026, 3, 1), payment_status=Order.PaymentStatus.PENDING)
        self.shipped(jst(2026, 3, 1), producer=make_producer(business_name="ほかの農園"))
        add_shipment(make_order(user=self.buyer), self.producer, items=((self.product, 3),))          # 未発送 3000＋1000
        add_shipment(make_order(user=self.buyer), self.producer, status=OrderShipment.Status.CANCEL_REQUESTED,
                     items=((self.product, 1),))                                                         # 1000＋1000
        add_shipment(make_order(user=self.buyer), self.producer, status=OrderShipment.Status.CANCELED)

        data = self.client.get(URL, {"year": 2026}).json()
        self.assertEqual(data["monthly"][0], {"month": 1, "shipmentCount": 2, "salesAmount": 5000})
        self.assertEqual(data["monthly"][10], {"month": 11, "shipmentCount": 1, "salesAmount": 2000})
        self.assertEqual(sum(m["shipmentCount"] for m in data["monthly"]), 3)
        self.assertEqual((data["year"], data["month"], data["feeRate"], data["items"]), (2026, None, 0, None))
        self.assertEqual(data["yearTotal"], {"shipmentCount": 3, "salesAmount": 7000})
        self.assertEqual(data["pending"], {"shipmentCount": 2, "amount": 6000})
        self.assertEqual(self.client.get(URL, {"year": 2025}).json()["yearTotal"]["shipmentCount"], 1)

    def test_month_items(self):
        old = self.shipped(jst(2026, 11, 1, 9), quantity=2)
        new = self.shipped(jst(2026, 11, 20, 9))
        self.shipped(jst(2026, 12, 1, 0, 0))
        data = self.client.get(URL, {"year": 2026, "month": 11, "pageSize": 1}).json()
        self.assertEqual((data["items"]["total"], data["items"]["totalPages"]), (2, 2))
        item = data["items"]["items"][0]
        self.assertEqual(item, {"shipmentId": new.id, "orderId": new.order_id, "orderNo": new.order.order_no,
                                "shippedAt": item["shippedAt"], "status": "shipped", "itemsTotal": 1000,
                                "shippingFee": 1000, "amount": 2000})
        page2 = self.client.get(URL, {"year": 2026, "month": 11, "pageSize": 1, "page": 2}).json()
        self.assertEqual(page2["items"]["items"][0]["shipmentId"], old.id)

    def test_default_year_and_validation(self):
        self.assertEqual(self.client.get(URL).json()["year"], timezone.localdate().year)
        for query in [{"year": 1999}, {"month": 13}, {"month": 0}, {"year": "x"}, {"sort": "new"}]:
            self.assertEqual(self.client.get(URL, query).status_code, 400, query)

    def test_permission(self):
        self.post_json("/api/v1/auth/signout")
        self.assertEqual(self.client.get(URL).status_code, 401)
        self.signin(self.buyer.email)
        self.assertEqual(self.client.get(URL).status_code, 403)
