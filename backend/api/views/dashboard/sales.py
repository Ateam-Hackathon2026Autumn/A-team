"""売上

認証: 生産者（承認済み。掲載停止中でも見られる）
仕様: api-spec.md「7. 実装で決めたこと」ステップ13（Notion には定義がない）

実装済み:
  - 売上: GET /api/v1/dashboard/sales?year=2026&month=11&page=1&pageSize=20
      ・支払い済みの注文の、自分の発送済み（shipped・delivered）の箱を、発送日時（shipped_at）の日本時間の月で集計
        1つの箱の売上＝明細の小計の合計＋送料（税込）。販売手数料は0%（feeRate: 0）
      ・monthly: 1〜12月の [{month, shipmentCount, salesAmount}]、yearTotal: {shipmentCount, salesAmount}
      ・pending: 入金予定＝今の未発送・キャンセル申請中の箱 {shipmentCount, amount}（年とは関係なし）
      ・month を付けると、その月の発送済みの箱の一覧を items に入れる（共通のページング。発送日時・id の新しい順）
        付けなければ items は null
      ・year の初期値は日本時間の今年（2000〜2100）
"""
from datetime import datetime

from django.db.models import Count, IntegerField, OuterRef, Subquery, Sum, Value
from django.db.models.functions import Coalesce, ExtractMonth
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from marche.models import Order, OrderItem, OrderShipment

from ...common.pagination import paginate, validate_query
from ...common.permissions import IsApprovedProducer
from ...serializers.dashboard.sales import SalesQuerySerializer, SalesShipmentSerializer

SHIPPED = [OrderShipment.Status.SHIPPED, OrderShipment.Status.DELIVERED]
PENDING = [OrderShipment.Status.UNSHIPPED, OrderShipment.Status.CANCEL_REQUESTED]
FEE_RATE = 0


def month_start(year, month):
    """日本時間（settings.TIME_ZONE）の月初の日時"""
    return timezone.make_aware(datetime(year, month, 1))


def next_month_start(year, month):
    return month_start(year + 1, 1) if month == 12 else month_start(year, month + 1)


def items_total():
    total = (OrderItem.objects.filter(shipment=OuterRef("pk")).order_by().values("shipment")
             .annotate(t=Sum("subtotal")).values("t")[:1])
    return Coalesce(Subquery(total, output_field=IntegerField()), Value(0))


def amount_of(shipments):
    """箱の売上の合計（明細の小計＋送料）"""
    items = OrderItem.objects.filter(shipment__in=shipments).aggregate(t=Sum("subtotal"))["t"] or 0
    return items + (shipments.aggregate(t=Sum("shipping_fee"))["t"] or 0)


class DashboardSalesView(APIView):
    """GET /api/v1/dashboard/sales"""

    permission_classes = [IsApprovedProducer]

    def get(self, request):
        query = validate_query(SalesQuerySerializer, request)
        year = query.get("year") or timezone.localdate().year
        month = query.get("month")
        paid = OrderShipment.objects.filter(producer=request.user.producer,
                                            order__payment_status=Order.PaymentStatus.PAID)
        shipped = paid.filter(status__in=SHIPPED,
                              shipped_at__gte=month_start(year, 1), shipped_at__lt=month_start(year + 1, 1))

        tz = timezone.get_current_timezone()
        by_month = list(shipped.annotate(m=ExtractMonth("shipped_at", tzinfo=tz)).order_by()
                        .values("m").annotate(c=Count("id"), f=Sum("shipping_fee")))
        counts = {r["m"]: r["c"] for r in by_month}
        fees = {r["m"]: r["f"] or 0 for r in by_month}
        item_sums = {r["m"]: r["t"] or 0 for r in OrderItem.objects.filter(shipment__in=shipped)
                     .annotate(m=ExtractMonth("shipment__shipped_at", tzinfo=tz)).order_by()
                     .values("m").annotate(t=Sum("subtotal")).values("m", "t")}
        monthly = [{"month": m, "shipment_count": counts.get(m, 0),
                    "sales_amount": item_sums.get(m, 0) + fees.get(m, 0)} for m in range(1, 13)]

        pending = paid.filter(status__in=PENDING)
        body = {
            "year": year,
            "month": month,
            "fee_rate": FEE_RATE,
            "monthly": monthly,
            "year_total": {"shipment_count": sum(r["shipment_count"] for r in monthly),
                           "sales_amount": sum(r["sales_amount"] for r in monthly)},
            "pending": {"shipment_count": pending.count(), "amount": amount_of(pending)},
            "items": None,
        }
        if month is not None:
            in_month = shipped.filter(shipped_at__gte=month_start(year, month),
                                      shipped_at__lt=next_month_start(year, month))
            rows = (in_month.select_related("order").annotate(items_total=items_total())
                    .order_by("-shipped_at", "-id"))
            body["items"] = paginate(rows, query, SalesShipmentSerializer, count_queryset=in_month)
        return Response(body)
