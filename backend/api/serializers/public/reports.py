"""通報 のシリアライザー

使う view: api/views/public/reports.py

  - 通報（POST /api/v1/reports）: ReportCreateSerializer {targetType, targetId, reason, detail}
      ・targetType は reports.target_type の6種類のうち、今は product・experience・job・producer だけ受け付ける
        （story は拡張の「ストーリー記事」、user はチャットと一緒に作る。どちらも今は 400）
      ・reason は REPORT_REASONS のコード（reports.reason は VARCHAR(30) で選択肢がDBにないため、ここで決める）

入力エラーは 400（項目ごとのメッセージ）。カラム名は claude/er-diagram.md に合わせる
"""
from rest_framework import serializers

from marche.models import Report

from ...common.serializers import StrictSerializer

MAX_ID = 2 ** 63 - 1

# 通報理由（コード → 画面の表示名）。運営の画面でも表示名に使う
REPORT_REASONS = {
    "inappropriate": "不適切な内容",
    "fraud": "詐欺・虚偽",
    "spam": "宣伝・スパム",
    "rights": "権利の侵害",
    "harassment": "嫌がらせ",
    "other": "その他",
}

# 今通報できる対象の種類
REPORTABLE_TYPES = [Report.TargetType.PRODUCT, Report.TargetType.EXPERIENCE, Report.TargetType.JOB,
                    Report.TargetType.PRODUCER]


class ReportCreateSerializer(StrictSerializer):
    target_type = serializers.ChoiceField(choices=Report.TargetType.choices)
    target_id = serializers.IntegerField(min_value=1, max_value=MAX_ID)
    reason = serializers.ChoiceField(choices=list(REPORT_REASONS.items()))
    detail = serializers.CharField(max_length=1000, required=False, allow_blank=True, allow_null=True)

    def validate_target_type(self, value):
        if value == Report.TargetType.STORY:
            raise serializers.ValidationError("農園のページの問題は、生産者（producer）として通報してください。")
        if value not in REPORTABLE_TYPES:
            raise serializers.ValidationError("この種類は、まだ通報できません。")
        return value

    def validate_detail(self, value):
        return value or None
