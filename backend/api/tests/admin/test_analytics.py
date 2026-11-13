"""分析（運営） のテスト

テスト対象: api/views/admin/analytics.py
  - 分析: GET /api/v1/admin/analytics（月ごとの売上・新規ユーザー・注文・体験予約・求人応募、売上上位の生産者）
"""
from datetime import datetime

from django.utils import timezone

from marche.models import JobApplication, Order, OrderShipment, Reservation, User

from ..utils import (ApiTestCase, add_shipment, make_experience, make_job, make_job_application, make_order,
                     make_producer, make_product, make_reservation, make_slot, make_user)
from .test_producer_applications import make_staff

BASE = "/api/v1/admin/analytics"


def jst(*args):
    return timezone.make_aware(datetime(*args))


class AdminAnalyticsTests(ApiTestCase):
    def test_monthly_and_top(self):
        staff = make_staff("admin@example.com", "管理者")
        yamada = make_producer(business_name="山田農園")
        sato = make_producer(business_name="佐藤牧場")
        buyer = make_user(email="buyer@example.com")
        User.objects.exclude(pk=buyer.pk).update(date_joined=jst(2025, 6, 1))
        User.objects.filter(pk=buyer.pk).update(date_joined=jst(2026, 3, 1, 0, 30))   # 日本時間で3月
        for producer, quantity, at in [(yamada, 3, jst(2026, 1, 1, 0, 30)), (sato, 1, jst(2026, 1, 20)),
                                       (sato, 1, jst(2026, 2, 5))]:
            add_shipment(make_order(user=buyer, ordered_at=at), producer,
                         items=((make_product(producer), quantity),), status=OrderShipment.Status.SHIPPED,
                         shipped_at=at)
        add_shipment(make_order(user=buyer, ordered_at=jst(2026, 1, 5), payment_status=Order.PaymentStatus.PENDING),
                     yamada, items=((make_product(yamada), 1),))                       # 数えない
        reservation = make_reservation(make_slot(make_experience(yamada)), user=buyer)
        Reservation.objects.filter(pk=reservation.pk).update(created_at=jst(2026, 4, 1))
        application = make_job_application(make_job(sato), user=buyer)
        JobApplication.objects.filter(pk=application.pk).update(created_at=jst(2026, 4, 2))

        self.signin(staff.email)
        data = self.client.get(BASE, {"year": 2026}).json()
        self.assertEqual(data["monthly"][0], {"month": 1, "salesAmount": 6000, "shipmentCount": 2, "newUsers": 0,
                                              "orders": 2, "experienceReservations": 0, "jobApplications": 0})
        self.assertEqual((data["monthly"][2]["newUsers"], data["monthly"][3]["experienceReservations"],
                          data["monthly"][3]["jobApplications"]), (1, 1, 1))
        self.assertEqual(data["yearTotal"], {"salesAmount": 8000, "shipmentCount": 3, "newUsers": 1, "orders": 3,
                                             "experienceReservations": 1, "jobApplications": 1})
        self.assertEqual(data["topProducers"], [
            {"producerId": yamada.id, "businessName": "山田農園", "salesAmount": 4000, "shipmentCount": 1},
            {"producerId": sato.id, "businessName": "佐藤牧場", "salesAmount": 4000, "shipmentCount": 2}][
            ::1 if yamada.id < sato.id else -1])
        self.assertEqual(self.client.get(BASE).json()["year"], timezone.localdate().year)
        self.assertEqual(self.client.get(BASE, {"year": 1999}).status_code, 400)
