"""生産者ダッシュボード

認証: 生産者（承認済み。掲載停止中でも見られる）
仕様: api-spec.md「7. 実装で決めたこと」ステップ13。Notion の定義（ダッシュボード集計取得API）＋api-spec の「対応が必要な数」

実装済み:
  - 生産者ダッシュボード: GET /api/v1/dashboard/summary（クエリなし）
      ・publishedProductCount・publishedExperienceCount・publishedJobCount: 公開中の数。農園が公開中のときだけ数える
        （非公開・下書き・停止中なら3つとも0。お客さんから見える数のため）
      ・experienceApplicationCount・jobApplicationCount: 体験の申込・求人の応募の累計（全状態の件数）
      ・sales {currency, scope, grossAmount, refundedAmount, netAmount}: 全期間・商品の注文だけ（体験は当日払いなので入れない）
        支払い済みの注文の自分の箱ごとに「明細の小計の合計＋送料」を grossAmount に、返金額（refunded_amount）を
        refundedAmount に足す。キャンセルされた箱も両方に残す。netAmount＝差
      ・todo {unshippedCount, cancelRequestedCount, upcomingReservationCount, newJobApplicationCount}: 対応が必要な数
        （支払い済みの未発送の箱・キャンセル申請中の箱・開催前の確定済みの予約・applied の応募）
      ・asOf: 集計した日時。全部を1つのトランザクションの中で読む
"""
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from marche.models import (Experience, Job, JobApplication, Order, OrderItem, OrderShipment, Product, PublishStatus,
                           Reservation)

from ...common.pagination import validate_query
from ...common.permissions import IsApprovedProducer
from ...serializers.dashboard.summary import SummaryQuerySerializer


def published_count(model, producer):
    if producer.publish_status != PublishStatus.PUBLIC:
        return 0
    return model.objects.filter(producer=producer, publish_status=PublishStatus.PUBLIC).count()


def paid_shipments(producer):
    return OrderShipment.objects.filter(producer=producer, order__payment_status=Order.PaymentStatus.PAID)


class DashboardSummaryView(APIView):
    """GET /api/v1/dashboard/summary"""

    permission_classes = [IsApprovedProducer]

    def get(self, request):
        validate_query(SummaryQuerySerializer, request)
        producer = request.user.producer
        now = timezone.now()
        with transaction.atomic():
            items_total = OrderItem.objects.filter(
                shipment__producer=producer, shipment__order__payment_status=Order.PaymentStatus.PAID,
            ).aggregate(total=Sum("subtotal"))["total"] or 0
            shipments = paid_shipments(producer).aggregate(
                shipping=Sum("shipping_fee"), refunded=Sum("refunded_amount"),
                unshipped=Count("id", filter=Q(status=OrderShipment.Status.UNSHIPPED)),
                cancel_requested=Count("id", filter=Q(status=OrderShipment.Status.CANCEL_REQUESTED)))
            reservations = Reservation.objects.filter(slot__experience__producer=producer).aggregate(
                total=Count("id"),
                upcoming=Count("id", filter=Q(status=Reservation.Status.CONFIRMED, slot__start_at__gte=now)))
            applications = JobApplication.objects.filter(job__producer=producer).aggregate(
                total=Count("id"), new=Count("id", filter=Q(status=JobApplication.Status.APPLIED)))
            gross = items_total + (shipments["shipping"] or 0)
            refunded = shipments["refunded"] or 0
            body = {
                "as_of": now,
                "published_product_count": published_count(Product, producer),
                "published_experience_count": published_count(Experience, producer),
                "published_job_count": published_count(Job, producer),
                "experience_application_count": reservations["total"],
                "job_application_count": applications["total"],
                "sales": {"currency": "JPY", "scope": "product_orders", "gross_amount": gross,
                          "refunded_amount": refunded, "net_amount": gross - refunded},
                "todo": {
                    "unshipped_count": shipments["unshipped"],
                    "cancel_requested_count": shipments["cancel_requested"],
                    "upcoming_reservation_count": reservations["upcoming"],
                    "new_job_application_count": applications["new"],
                },
            }
        return Response(body)
