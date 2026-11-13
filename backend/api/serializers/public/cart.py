"""カート のシリアライザー（リクエストの検証だけ）

使う view: api/views/public/cart.py
レスポンスは services/cart.py の build_cart() が組み立てる:
  {items: [{id, productId, productName, volume, thumbnailUrl, quantity, unitPrice, subtotal, purchasable,
            unavailableReason}],
   shipments: [{producerId, producerName, temperatureZone, itemIds, itemsTotal, shippingFee, freeShippingThreshold}],
   itemsTotal, shippingTotal, total, canCheckout}
"""
from rest_framework import serializers

from ...common.serializers import StrictSerializer
from ...services.cart import MAX_QUANTITY

MAX_ID = 2 ** 63 - 1
QUANTITY_ERRORS = {"max_value": f"1つの商品は{MAX_QUANTITY}個までです。", "min_value": "1以上の数を指定してください。"}


class CartItemAddSerializer(StrictSerializer):
    """POST /cart/items の本文 {productId, quantity}（quantity は追加する数）"""

    product_id = serializers.IntegerField(min_value=1, max_value=MAX_ID)
    quantity = serializers.IntegerField(min_value=1, max_value=MAX_QUANTITY, error_messages=QUANTITY_ERRORS)


class CartItemUpdateSerializer(StrictSerializer):
    """PATCH /cart/items/:itemId の本文 {quantity}（変更後の数。0 は使わず削除APIで）"""

    quantity = serializers.IntegerField(min_value=1, max_value=MAX_QUANTITY, error_messages=QUANTITY_ERRORS)
