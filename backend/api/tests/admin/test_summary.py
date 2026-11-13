"""運営ダッシュボード のテスト

テスト対象: api/views/admin/summary.py
  - 運営ダッシュボード: GET /api/v1/admin/summary
      ・新規ユーザー・生産者申請・注文・体験申込・求人応募（今日・7日・30日。日本時間）
      ・未対応件数（審査待ち・問い合わせ open・通報 open・キャンセル申請中・返金待ち）
"""
from datetime import timedelta

from django.utils import timezone

from marche.models import Inquiry, Order, OrderShipment, ProducerApplication, Report, User

from ..utils import (ApiTestCase, add_shipment, make_experience, make_job, make_job_application, make_order,
                     make_producer, make_reservation, make_slot, make_user)
from .test_producer_applications import make_application, make_staff

URL = "/api/v1/admin/summary"


def midnight():
    return timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)


class AdminSummaryTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.staff = make_staff("cs@example.com", "CS")
        self.signin(self.staff.email)

    def test_counts(self):
        today, yesterday = midnight() + timedelta(minutes=1), midnight() - timedelta(minutes=1)
        for email, joined in [("a@example.com", today), ("b@example.com", yesterday),
                              ("c@example.com", midnight() - timedelta(days=10)),
                              ("d@example.com", midnight() - timedelta(days=40))]:
            make_user(email=email, date_joined=joined)
        application = make_application(business_name="申請中の農園", submitted_at=today)
        producer = make_producer(business_name="山田農園")
        User.objects.filter(pk__in=[producer.user_id, application.producer.user_id]).update(
            date_joined=midnight() - timedelta(days=100))
        make_order(user=make_user(email="old@example.com", date_joined=midnight() - timedelta(days=100)),
                   ordered_at=today)
        make_order(ordered_at=yesterday)
        make_order(ordered_at=today, payment_status=Order.PaymentStatus.PENDING)    # 数えない
        experience = make_experience(producer)
        reservation = make_reservation(make_slot(experience), user=User.objects.get(email="old@example.com"))
        job = make_job(producer)
        job_application = make_job_application(job, user=User.objects.get(email="old@example.com"))
        type(job_application).objects.filter(pk=job_application.pk).update(created_at=midnight() - timedelta(days=8))
        type(reservation).objects.filter(pk=reservation.pk).update(created_at=today)

        Inquiry.objects.create(email="x@example.com", category="other", subject="s", body="b")
        Inquiry.objects.create(email="x@example.com", category="other", subject="s", body="b", status="closed")
        reporter = User.objects.get(email="a@example.com")
        Report.objects.create(reporter=reporter, target_type="product", target_id=1, reason="spam")
        order = make_order(user=reporter, ordered_at=midnight() - timedelta(days=50))
        add_shipment(order, producer, status=OrderShipment.Status.CANCEL_REQUESTED)
        add_shipment(order, producer, status=OrderShipment.Status.CANCELED, temperature_zone="frozen")
        add_shipment(order, producer, status=OrderShipment.Status.CANCELED, temperature_zone="chilled",
                     refunded_amount=2000)

        with self.assertNumQueries(14):  # 権限（セッション・ユーザー・グループ）＋SAVEPOINT・RELEASE＋集計9本
            data = self.client.get(URL).json()
        self.assertIsNotNone(data.pop("asOf"))
        self.assertEqual(data["today"], {"newUsers": 1, "newProducerApplications": 1, "orders": 1,
                                         "experienceReservations": 1, "jobApplications": 0})
        self.assertEqual(data["last7Days"], {"newUsers": 2, "newProducerApplications": 1, "orders": 2,
                                             "experienceReservations": 1, "jobApplications": 0})
        self.assertEqual(data["last30Days"]["newUsers"], 3)
        self.assertEqual(data["last30Days"]["jobApplications"], 1)
        self.assertEqual(data["pending"], {"producerApplications": 1, "inquiries": 1, "reports": 1,
                                           "cancelRequests": 1, "refunds": 1})

    def test_staff_not_counted_and_groups(self):
        make_staff("reviewer@example.com", "審査担当")
        self.assertEqual(self.client.get(URL).json()["today"]["newUsers"], 0)
        self.assertEqual(self.client.get(URL, {"x": "1"}).status_code, 400)
        for email in ["reviewer@example.com"]:
            self.post_json("/api/v1/admin/auth/signout")
            self.signin(email)
            self.assertEqual(self.client.get(URL).status_code, 200)
        self.post_json("/api/v1/admin/auth/signout")
        self.signin(make_user(email="buyer@example.com").email)
        self.assertEqual(self.client.get(URL).status_code, 403)
        self.assertEqual(ProducerApplication.objects.count(), 0)
