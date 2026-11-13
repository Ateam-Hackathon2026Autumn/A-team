"""配送設定（生産者） のシリアライザー

使う view: api/views/dashboard/shipping_settings.py
Notion には定義がないので、形は api-spec.md と「7. 実装で決めたこと」で決めた。
- 1件: {id, temperatureZone, shippingFee, freeShippingThreshold, leadTimeText}
- 保存（PUT）: {items: [...]}。温度帯ごとにまとめて置き換える（id は送らない。温度帯で突き合わせる）
"""
from rest_framework import serializers

from marche.models import ShippingSetting

from ...common.serializers import StrictSerializer

MAX_INT = 2 ** 31 - 1


class ShippingSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShippingSetting
        fields = ["id", "temperature_zone", "shipping_fee", "free_shipping_threshold", "lead_time_text"]


class ShippingSettingItemSerializer(StrictSerializer):
    """保存する1件。freeShippingThreshold は空なら送料無料にしない"""

    temperature_zone = serializers.ChoiceField(choices=ShippingSetting.TemperatureZone.choices)
    shipping_fee = serializers.IntegerField(min_value=0, max_value=MAX_INT)
    free_shipping_threshold = serializers.IntegerField(min_value=0, max_value=MAX_INT, required=False,
                                                       allow_null=True)
    lead_time_text = serializers.CharField(max_length=50)


class ShippingSettingsUpdateSerializer(StrictSerializer):
    """PUT /dashboard/shipping-settings の本文 {items: [...]}（温度帯の重複は 400）"""

    items = ShippingSettingItemSerializer(many=True, max_length=len(ShippingSetting.TemperatureZone.choices))

    def validate_items(self, items):
        zones = [item["temperature_zone"] for item in items]
        if len(zones) != len(set(zones)):
            raise serializers.ValidationError("同じ温度帯を複数指定することはできません。")
        return items
