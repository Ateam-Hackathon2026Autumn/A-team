"""運営ダッシュボード

認証: 管理者（権限グループ: 全グループ。審査担当・CS・管理者）
仕様: api-spec.md「7. 実装で決めたこと」ステップ14（Notion にはシーケンス図「管理者ログイン・運営ダッシュボード」と名前だけ）

実装済み:
  - 運営ダッシュボード: GET /api/v1/admin/summary（クエリなし）
      ・today・last7Days・last30Days: {newUsers, newProducerApplications, orders, experienceReservations, jobApplications}
        日本時間の日付で数える（7日・30日は今日を含む）。新規ユーザーは運営スタッフを除く。注文は支払い済みだけ（注文日時）
      ・pending: 未対応の件数 {producerApplications（審査待ち）, inquiries（open）, reports（open）,
        cancelRequests（支払い済みの注文のキャンセル申請中の箱）, refunds（返金待ち＝canceled で返金額が空の箱）}
      ・asOf: 集計した日時。全部を1つのトランザクションの中で読む
"""
from datetime import timedelta

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from marche.models import (Inquiry, JobApplication, Order, OrderShipment, ProducerApplication, Report, Reservation,
                           User)

from ...common.pagination import validate_query
from ...common.permissions import CS_GROUP, REVIEWER_GROUP, AdminGroupPermission
from ...common.serializers import QuerySerializer

PERIODS = {"today": 0, "last7_days": 6, "last30_days": 29}


def period_starts(now):
    """各期間の始まり（日本時間の0時）"""
    midnight = timezone.localtime(now).replace(hour=0, minute=0, second=0, microsecond=0)
    return {name: midnight - timedelta(days=days) for name, days in PERIODS.items()}


def counts_by_period(queryset, field, starts):
    """期間ごとの件数を1本の SQL で数える"""
    result = queryset.aggregate(**{name: Count("id", filter=Q(**{f"{field}__gte": start}))
                                   for name, start in starts.items()})
    return {name: result[name] for name in starts}


class AdminSummaryView(APIView):
    """GET /api/v1/admin/summary"""

    permission_classes = [AdminGroupPermission]
    admin_groups = [REVIEWER_GROUP, CS_GROUP]

    def get(self, request):
        validate_query(QuerySerializer, request)  # クエリは受け付けない
        now = timezone.now()
        starts = period_starts(now)
        oldest = min(starts.values())
        with transaction.atomic():
            sources = {
                "new_users": counts_by_period(User.objects.filter(is_staff=False, date_joined__gte=oldest),
                                              "date_joined", starts),
                "new_producer_applications": counts_by_period(
                    ProducerApplication.objects.filter(submitted_at__gte=oldest), "submitted_at", starts),
                "orders": counts_by_period(
                    Order.objects.filter(payment_status=Order.PaymentStatus.PAID, ordered_at__gte=oldest),
                    "ordered_at", starts),
                "experience_reservations": counts_by_period(Reservation.objects.filter(created_at__gte=oldest),
                                                            "created_at", starts),
                "job_applications": counts_by_period(JobApplication.objects.filter(created_at__gte=oldest),
                                                     "created_at", starts),
            }
            paid = OrderShipment.objects.filter(order__payment_status=Order.PaymentStatus.PAID).aggregate(
                cancel_requests=Count("id", filter=Q(status=OrderShipment.Status.CANCEL_REQUESTED)),
                refunds=Count("id", filter=Q(status=OrderShipment.Status.CANCELED, refunded_amount__isnull=True)))
            pending = {
                "producer_applications": ProducerApplication.objects.filter(
                    status=ProducerApplication.Status.PENDING).count(),
                "inquiries": Inquiry.objects.filter(status=Inquiry.Status.OPEN).count(),
                "reports": Report.objects.filter(status=Report.Status.OPEN).count(),
                **paid,
            }
        body = {"as_of": now, "pending": pending}
        for period in PERIODS:
            body[period] = {key: values[period] for key, values in sources.items()}
        return Response(body)
