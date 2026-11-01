"""シリアライザーの共通部品"""
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
