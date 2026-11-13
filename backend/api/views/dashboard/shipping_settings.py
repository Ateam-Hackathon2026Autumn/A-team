"""配送設定（生産者）

認証: 承認済みの生産者（IsApprovedProducer）。掲載停止中でも配送設定は変えられる（api-spec「生産者APIの共通チェック」）
仕様: api-spec.md＋「7. 実装で決めたこと」（Notion には定義なし）。カラム名: claude/er-diagram.md

このファイルの API:
    - 配送設定取得: GET /api/v1/dashboard/shipping-settings
        ・{items: [...]}。温度帯の順（常温・冷蔵・冷凍）
    - 配送設定保存: PUT /api/v1/dashboard/shipping-settings
        ・{items: [...]} で温度帯ごとにまとめて置き換える
        ・同じ温度帯の行は id を変えずに更新する（商品の shipping_setting_id が切れないように）
        ・送られなかった温度帯は削除する。商品が使っていれば 409 SHIPPING_SETTING_IN_USE（何も変えない）
"""
from django.db import transaction
from django.db.models import Case, IntegerField, Value, When
from rest_framework.response import Response
from rest_framework.views import APIView

from marche.models import Product, ShippingSetting

from ...common.exceptions import Conflict
from ...common.pagination import validate_query
from ...common.permissions import IsApprovedProducer
from ...common.serializers import QuerySerializer
from ...serializers.dashboard.shipping_settings import ShippingSettingSerializer, ShippingSettingsUpdateSerializer

ZONE_ORDER = [zone for zone, _ in ShippingSetting.TemperatureZone.choices]


def my_settings(producer):
    order = Case(*[When(temperature_zone=zone, then=Value(i)) for i, zone in enumerate(ZONE_ORDER)],
                 output_field=IntegerField())
    return ShippingSetting.objects.filter(producer=producer).order_by(order, "id")


def respond(producer):
    return Response({"items": ShippingSettingSerializer(my_settings(producer), many=True).data})


class ShippingSettingsView(APIView):
    """GET・PUT /api/v1/dashboard/shipping-settings"""

    permission_classes = [IsApprovedProducer]

    def get(self, request):
        validate_query(QuerySerializer, request)  # クエリパラメーターは受け付けない
        return respond(request.user.producer)

    def put(self, request):
        serializer = ShippingSettingsUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        items = {item["temperature_zone"]: item for item in serializer.validated_data["items"]}
        producer = request.user.producer

        with transaction.atomic():
            current = {setting.temperature_zone: setting
                       for setting in ShippingSetting.objects.select_for_update().filter(producer=producer)}
            removed = [setting for zone, setting in current.items() if zone not in items]
            if removed and Product.objects.filter(shipping_setting__in=removed).exists():
                raise Conflict("SHIPPING_SETTING_IN_USE",
                               "商品で使っている温度帯は削除できません。先に商品の配送設定を変えてください。")
            ShippingSetting.objects.filter(pk__in=[setting.pk for setting in removed]).delete()

            for zone, item in items.items():
                setting = current.get(zone) or ShippingSetting(producer=producer, temperature_zone=zone)
                setting.shipping_fee = item["shipping_fee"]
                setting.free_shipping_threshold = item.get("free_shipping_threshold")
                setting.lead_time_text = item["lead_time_text"]
                setting.save()
        return respond(producer)
