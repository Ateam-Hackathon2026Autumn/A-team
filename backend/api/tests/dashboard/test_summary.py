"""生産者ダッシュボード のテスト

テスト対象: api/views/dashboard/summary.py
  - 生産者ダッシュボード: GET /api/v1/dashboard/summary
      ・公開中の数（農園が公開中のときだけ）・申込と応募の累計・売上（全期間・返金を引く）・対応が必要な数
"""
from marche.models import Order, OrderShipment, PublishStatus, Reservation

from ..utils import (ApiTestCase, add_shipment, make_experience, make_job, make_job_application, make_order,
                     make_producer, make_product, make_reservation, make_slot, make_user)

URL = "/api/v1/dashboard/summary"
ZERO_SALES = {"currency": "JPY", "scope": "product_orders", "grossAmount": 0, "refundedAmount": 0, "netAmount": 0}


class SummaryTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.producer = make_producer(business_name="山田農園")
        self.signin(self.producer.user.email)

    def test_empty(self):
        data = self.client.get(URL).json()
        self.assertIsNotNone(data.pop("asOf"))
        self.assertEqual(data, {
            "publishedProductCount": 0, "publishedExperienceCount": 0, "publishedJobCount": 0,
            "experienceApplicationCount": 0, "jobApplicationCount": 0, "sales": ZERO_SALES,
            "todo": {"unshippedCount": 0, "cancelRequestedCount": 0, "upcomingReservationCount": 0,
                     "newJobApplicationCount": 0}})

    def test_counts(self):
        other = make_producer(business_name="ほかの農園")
        carrot = make_product(self.producer)
        make_product(self.producer, name="下書き", publish_status=PublishStatus.DRAFT)
        make_product(other)
        experience = make_experience(self.producer, publish_status=PublishStatus.PUBLIC)
        job = make_job(self.producer)
        make_job(self.producer, title="非公開", publish_status=PublishStatus.PRIVATE)
        buyer = make_user(email="buyer@example.com")
        make_reservation(make_slot(experience, days=7), user=buyer)                           # これから
        make_reservation(make_slot(experience, days=-7), user=buyer, status=Reservation.Status.ATTENDED)
        make_reservation(make_slot(experience, days=14), user=buyer, status=Reservation.Status.CANCELED)
        make_job_application(job, user=buyer)
        make_job_application(job, user=make_user(email="b2@example.com"), status="rejected")

        order = make_order(user=buyer)
        add_shipment(order, self.producer, items=((carrot, 2),))                                    # 2000＋1000
        add_shipment(order, self.producer, items=((carrot, 1),), temperature_zone="frozen",
                     status=OrderShipment.Status.CANCELED, refunded_amount=2000)                   # 1000＋1000
        add_shipment(make_order(user=buyer), self.producer, items=((carrot, 1),),
                     status=OrderShipment.Status.CANCEL_REQUESTED)                                 # 1000＋1000
        add_shipment(make_order(user=buyer, payment_status=Order.PaymentStatus.PENDING), self.producer,
                     items=((carrot, 1),))                                                         # 数えない
        add_shipment(order, other, items=((make_product(other, name="別"), 1),))                     # ほかの農園

        with self.assertNumQueries(12):  # 生産者の確認（セッション・ユーザー・生産者）＋SAVEPOINT・RELEASE＋集計7本
            data = self.client.get(URL).json()
        self.assertEqual(
            (data["publishedProductCount"], data["publishedExperienceCount"], data["publishedJobCount"],
             data["experienceApplicationCount"], data["jobApplicationCount"]), (1, 1, 1, 3, 2))
        self.assertEqual(data["sales"], {"currency": "JPY", "scope": "product_orders", "grossAmount": 7000,
                                         "refundedAmount": 2000, "netAmount": 5000})
        self.assertEqual(data["todo"], {"unshippedCount": 1, "cancelRequestedCount": 1,
                                        "upcomingReservationCount": 1, "newJobApplicationCount": 1})

    def test_private_producer_has_no_published(self):
        make_product(self.producer)
        self.producer.publish_status = PublishStatus.PRIVATE
        self.producer.save()
        self.assertEqual(self.client.get(URL).json()["publishedProductCount"], 0)
        self.producer.publish_status = PublishStatus.SUSPENDED   # 掲載停止中でも見られる
        self.producer.save()
        self.assertEqual(self.client.get(URL).status_code, 200)

    def test_permission_and_query(self):
        self.assertEqual(self.client.get(URL, {"year": "2026"}).status_code, 400)
        self.post_json("/api/v1/auth/signout")
        self.assertEqual(self.client.get(URL).status_code, 401)
        pending = make_producer(user=make_user(email="new@example.com"), approval="pending")
        self.signin(pending.user.email)
        self.assertEqual(self.client.get(URL).status_code, 403)
