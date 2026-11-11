"""ストーリー管理（学ぶページ） のシリアライザー

使う view: api/views/dashboard/story.py

  - 取得・保存のレスポンス: DashboardStorySerializer {craft, method, process, environment, reason, goal, publishStatus, updatedAt}
      ・ER図の producer_stories の形（Notion の title・storyCategoryId・category は拡張のストーリー記事の項目なので使わない）
  - 保存の本文: StoryPutSerializer（PUT なので7項目すべて必須）
      ・本文6項目は null か2,000文字までの文字列（前後の空白を除き、空なら null）
      ・publishStatus は draft・public・private

入力エラーは 400（項目ごとのメッセージ）。カラム名は claude/er-diagram.md に合わせる
"""
from rest_framework import serializers

from marche.models import ProducerStory, PublishStatus

from ...common.serializers import StrictSerializer

STORY_TEXT_FIELDS = ["craft", "method", "process", "environment", "reason", "goal"]
MAX_TEXT = 2000


class DashboardStorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProducerStory
        fields = STORY_TEXT_FIELDS + ["publish_status", "updated_at"]


def empty_story():
    """行がないときの取得結果"""
    return {**{f: None for f in STORY_TEXT_FIELDS}, "publish_status": PublishStatus.DRAFT, "updated_at": None}


def _text_field():
    return serializers.CharField(max_length=MAX_TEXT, allow_null=True, allow_blank=True)


class StoryPutSerializer(StrictSerializer):
    craft = _text_field()
    method = _text_field()
    process = _text_field()
    environment = _text_field()
    reason = _text_field()
    goal = _text_field()
    publish_status = serializers.ChoiceField(
        choices=[PublishStatus.DRAFT, PublishStatus.PUBLIC, PublishStatus.PRIVATE])

    def validate(self, attrs):
        for field in STORY_TEXT_FIELDS:
            attrs[field] = attrs[field] or None
        if attrs["publish_status"] == PublishStatus.PUBLIC and not any(attrs[f] for f in STORY_TEXT_FIELDS):
            raise serializers.ValidationError({"publish_status": ["公開するには本文を1項目以上入力してください。"]})
        return attrs
