"""分析（運営）

認証: 管理者（権限グループ: 管理者）
仕様: api-spec.md「7. 実装で決めたこと」ステップ16（Notion には API の名前だけ）

実装済み:
  - 分析（管理者）: GET /api/v1/admin/analytics?year=2026（初期値は日本時間の今年）
      ・monthly: 1〜12月の [{month, salesAmount, shipmentCount, newUsers, orders, experienceReservations, jobApplications}]
        売上は生産者の売上画面（dashboard/sales.py）と同じ数え方: 支払い済みの発送済み（shipped・delivered）の箱を
        shipped_at の日本時間の月で集計（明細の小計＋送料）。新規ユーザーは運営スタッフを除く。注文は支払い済み（注文日時）
      ・yearTotal: 年の合計
      ・topProducers: その年の売上上位20の生産者 [{producerId, businessName, salesAmount, shipmentCount}]
"""
from django.db.models import Count, Sum
from django.db.models.functions import ExtractMonth
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from marche.models import JobApplication, Order, OrderItem, OrderShipment, Producer, Reservation, User

from ...common.pagination import validate_query
from ...common.permissions import AdminGroupPermission
from ...serializers.admin.settings import AnalyticsQuerySerializer
from ..dashboard.sales import SHIPPED, month_start

TOP_PRODUCERS = 20
METRICS = ["sales_amount", "shipment_count", "new_users", "orders", "experience_reservations", "job_applications"]


def by_month(queryset, field, tz, value=None):
    """{月: 値}（value を省略したら件数）"""
    rows = (queryset.annotate(m=ExtractMonth(field, tzinfo=tz)).order_by().values("m")
            .annotate(v=value or Count("id")))
    return {r["m"]: r["v"] or 0 for r in rows}


class AdminAnalyticsView(APIView):
    """GET /api/v1/admin/analytics"""

    permission_classes = [AdminGroupPermission]

    def get(self, request):
        query = validate_query(AnalyticsQuerySerializer, request)
        year = query.get("year") or timezone.localdate().year
        start, end = month_start(year, 1), month_start(year + 1, 1)
        tz = timezone.get_current_timezone()

        shipped = OrderShipment.objects.filter(order__payment_status=Order.PaymentStatus.PAID, status__in=SHIPPED,
                                               shipped_at__gte=start, shipped_at__lt=end)
        items = OrderItem.objects.filter(shipment__in=shipped)
        item_sums = by_month(items, "shipment__shipped_at", tz, Sum("subtotal"))
        fees = by_month(shipped, "shipped_at", tz, Sum("shipping_fee"))
        series = {
            "shipment_count": by_month(shipped, "shipped_at", tz),
            "new_users": by_month(User.objects.filter(is_staff=False, date_joined__gte=start, date_joined__lt=end),
                                  "date_joined", tz),
            "orders": by_month(Order.objects.filter(payment_status=Order.PaymentStatus.PAID, ordered_at__gte=start,
                                                    ordered_at__lt=end), "ordered_at", tz),
            "experience_reservations": by_month(
                Reservation.objects.filter(created_at__gte=start, created_at__lt=end), "created_at", tz),
            "job_applications": by_month(
                JobApplication.objects.filter(created_at__gte=start, created_at__lt=end), "created_at", tz),
        }
        monthly = []
        for m in range(1, 13):
            row = {"month": m, "sales_amount": item_sums.get(m, 0) + fees.get(m, 0)}
            row.update({key: values.get(m, 0) for key, values in series.items()})
            monthly.append(row)

        return Response({
            "year": year,
            "monthly": monthly,
            "year_total": {key: sum(row[key] for row in monthly) for key in METRICS},
            "top_producers": self.top_producers(shipped, items),
        })

    @staticmethod
    def top_producers(shipped, items):
        item_sums = {r["shipment__producer"]: r["t"] for r in items.order_by().values("shipment__producer")
                     .annotate(t=Sum("subtotal"))}
        rows = shipped.order_by().values("producer").annotate(c=Count("id"), f=Sum("shipping_fee"))
        totals = [{"producer_id": r["producer"], "sales_amount": (item_sums.get(r["producer"]) or 0) + (r["f"] or 0),
                   "shipment_count": r["c"]} for r in rows]
        totals.sort(key=lambda r: (-r["sales_amount"], r["producer_id"]))
        totals = totals[:TOP_PRODUCERS]
        names = dict(Producer.objects.filter(pk__in=[r["producer_id"] for r in totals])
                     .values_list("pk", "business_name"))
        return [{"producer_id": r["producer_id"], "business_name": names.get(r["producer_id"]),
                 "sales_amount": r["sales_amount"], "shipment_count": r["shipment_count"]} for r in totals]
