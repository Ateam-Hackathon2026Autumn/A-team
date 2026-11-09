"""シリアライザーの共通部品"""
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import serializers


class StrictSerializer(serializers.Serializer):
    """定義にない項目が送られてきたら 400 にする（Notion の定義「未定義入力は拒否する」）

    使い方: リクエストを検証するシリアライザーは、serializers.Serializer の代わりにこれを継承する。
    """

    unknown_field_message = "この項目は受け付けていません。"

    def to_internal_value(self, data):
        if isinstance(data, dict):
            unknown = set(data) - set(self.fields)
            if unknown:
                raise serializers.ValidationError({name: [self.unknown_field_message] for name in sorted(unknown)})
        return super().to_internal_value(data)


class QuerySerializer(StrictSerializer):
    """クエリパラメーター（request.query_params）を検証する

    StrictSerializer の確認に加えて、同じ項目が2回以上ある（?page=1&page=2）ときも 400 にする。
    使い方: QuerySerializer を継承したクラスに data=request.query_params を渡す。
    """

    duplicate_message = "同じ項目を複数指定することはできません。"

    def to_internal_value(self, data):
        if hasattr(data, "getlist"):
            duplicated = sorted(key for key in data if len(data.getlist(key)) > 1)
            if duplicated:
                raise serializers.ValidationError({name: [self.duplicate_message] for name in duplicated})
            data = data.dict()
        return super().to_internal_value(data)


class QueryBooleanField(serializers.BooleanField):
    """クエリパラメーターの真偽値。"true" と "false" だけ受け付ける（大文字・0/1・yes などは 400）"""

    default_error_messages = {"invalid": "true または false を指定してください。"}

    def to_internal_value(self, data):
        if data in ("true", True):
            return True
        if data in ("false", False):
            return False
        self.fail("invalid")


class AwareDateTimeField(serializers.DateTimeField):
    """タイムゾーン付きの日時（例: 2026-12-01T10:00:00+09:00）だけを受け付ける

    タイムゾーンのない日時（2026-12-01T10:00:00）は、日本時間なのか UTC なのか分からないので 400 にする。
    """

    default_error_messages = {
        "naive": "タイムゾーン付きの日時（例: 2026-12-01T10:00:00+09:00）で指定してください。",
    }

    def to_internal_value(self, value):
        if isinstance(value, str):
            parsed = parse_datetime(value)
            if parsed is not None and timezone.is_naive(parsed):
                self.fail("naive")
        return super().to_internal_value(value)
