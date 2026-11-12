"""運営からのお知らせ（notices テーブル） のシリアライザー

使う view: api/views/public/announcements.py

実装済み:
  - AnnouncementListQuerySerializer: 一覧のクエリ（page・pageSize・audience（consumer（初期値）・producer））
  - AnnouncementSerializer: 一覧の1件 {id, title, audience, publishedAt}（本文は入れない）
  - AnnouncementDetailSerializer: 詳細 {id, title, body, audience, publishedAt}

入力エラーは 400（項目ごとのメッセージ）。カラム名は claude/er-diagram.md に合わせる
"""
from rest_framework import serializers

from marche.models import Notice

from ...common.pagination import PageQuerySerializer


class AnnouncementListQuerySerializer(PageQuerySerializer):
    audience = serializers.ChoiceField(choices=["consumer", "producer"], required=False, default="consumer")


class AnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notice
        fields = ["id", "title", "audience", "published_at"]


class AnnouncementDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notice
        fields = ["id", "title", "body", "audience", "published_at"]
