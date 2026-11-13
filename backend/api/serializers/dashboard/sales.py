"""売上 のシリアライザー

使う view: api/views/dashboard/sales.py

  - 売上（GET /api/v1/dashboard/sales）
      ・クエリ: year（省略すると日本時間の今年）・month（任意）・page・pageSize（month を付けたときの items 用）
      ・items の1件: SalesShipmentSerializer {shipmentId, orderId, orderNo, shippedAt, status, itemsTotal, shippingFee, amount}

入力エラーは 400（項目ごとのメッセージ）。カラム名は claude/er-diagram.md に合わせる
"""
from rest_framework import serializers

from ...common.pagination import PageQuerySerializer


class SalesQuerySerializer(PageQuerySerializer):
    year = serializers.IntegerField(required=False, min_value=2000, max_value=2100)
    month = serializers.IntegerField(required=False, min_value=1, max_value=12)


class SalesShipmentSerializer(serializers.Serializer):
    shipment_id = serializers.IntegerField(source="id")
    order_id = serializers.IntegerField()
    order_no = serializers.CharField(source="order.order_no")
    shipped_at = serializers.DateTimeField()
    status = serializers.CharField()
    items_total = serializers.IntegerField()
    shipping_fee = serializers.IntegerField()
    amount = serializers.SerializerMethodField()

    def get_amount(self, shipment):
        return shipment.items_total + shipment.shipping_fee
