"""生産者ダッシュボードの分析View"""

from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from api.common.permissions import IsApprovedProducer
from api.models import OrderShipment, OrderItem, FavoriteProduct
from api.serializers.dashboard.analytics import (
    AnalyticsQuerySerializer,
    AnalyticsResponseSerializer,
)


class AnalyticsView(APIView):
    """生産者ダッシュボードの分析API

    GET /api/v1/dashboard/analytics

    集計内容:
        ・月ごとの注文数
        ・月ごとの売上
        ・商品別販売数上位10件
        ・お気に入り数
    """

    permission_classes = [IsApprovedProducer]

    def get(self, request, *args, **kwargs):

        # クエリパラメータの検証
        query_serializer = AnalyticsQuerySerializer(
            data=request.query_params
        )

        if not query_serializer.is_valid():
            return Response(
                query_serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        year = query_serializer.validated_data.get(
            "year",
            timezone.localdate().year,
        )

        # ログイン中の生産者を取得
        producer = request.user.producer

        # 月ごとの注文数を集計
        monthly_orders = (
            OrderShipment.objects
            .filter(
                producer_id=producer.id,
                order__payment_status="paid",
                order__ordered_at__year=year,
            )
            .annotate(
                month=TruncMonth("order__ordered_at")
            )
            .values("month")
            .annotate(
                order_count=Count(
                    "order_id",
                    distinct=True,
                )
            )
            .order_by("month")
        )

        # 月ごとの売上を集計
        monthly_sales = (
            OrderItem.objects
            .filter(
                shipment__producer_id=producer.id,
                shipment__order__payment_status="paid",
                shipment__order__ordered_at__year=year,
            )
            .annotate(
                month=TruncMonth("shipment__order__ordered_at")
            )
            .values("month")
            .annotate(
                sales=Sum("subtotal")
            )
            .order_by("month")
        )

        # 注文数を月ごとに整理
        order_count_by_month = {
            item["month"].month: item["order_count"]
            for item in monthly_orders
        }

        # 売上を月ごとに整理
        sales_by_month = {
            item["month"].month: item["sales"] or 0
            for item in monthly_sales
        }

        # 1月から12月までのデータを作成
        monthly = []

        for month in range(1, 13):
            monthly.append({
                "month": month,
                "order_count": order_count_by_month.get(month, 0),
                "sales": sales_by_month.get(month, 0),
            })

        # 商品別販売数上位10件を取得
        top_products_queryset = (
            OrderItem.objects
            .filter(
                shipment__producer_id=producer.id,
                shipment__order__payment_status="paid",
                shipment__order__ordered_at__year=year,
            )
            .values(
                "product_id",
                "product_name",
            )
            .annotate(
                quantity=Sum("quantity")
            )
            .order_by(
                "-quantity",
                "product_id",
            )[:10]
        )

        top_products = list(top_products_queryset)

        # 生産者の商品のお気に入り数を取得
        favorite_count = FavoriteProduct.objects.filter(
            product__producer_id=producer.id,
        ).count()

        # レスポンスデータを作成
        response_data = {
            "year": year,
            "monthly": monthly,
            "top_products": top_products,
            "favorite_count": favorite_count,
        }

        # レスポンス形式を検証
        response_serializer = AnalyticsResponseSerializer(
            data=response_data
        )

        response_serializer.is_valid(raise_exception=True)

        return Response(
            response_serializer.data,
            status=status.HTTP_200_OK,
        )

# """分析

# 認証: 生産者
# 共通: 生産者APIの共通チェック（approved でなければ 403、掲載停止中にできない操作は 409）は common/permissions.py

# このファイルに書くもの（APIView / generics のクラス）。シーケンス図は Notion の同名の図:
#   - 分析（生産者）: GET /api/v1/dashboard/analytics
#       ・year。月ごとの注文数・売上、商品別販売数上位10、お気に入り数。アクセス数は拡張

# 仕様: claude/api-spec.md / カラム名: claude/er-diagram.md
# """
