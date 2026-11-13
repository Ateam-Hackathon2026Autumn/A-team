"""サイト内の通知・通知設定 のシリアライザー

使う view: api/views/public/notifications.py

実装済み:
  - NotificationListQuerySerializer: 通知一覧のクエリ（page・pageSize・unreadOnly）
  - NotificationSerializer: 通知1件 {id, notificationType, title, body, linkPath, isRead, readAt, createdAt}
  - NotificationSettingSerializer: 通知設定 {emailMessage, emailFavorite, emailNews}（PUT は3つとも必須）
      pushEnabled は Push 通知（拡張）用の列なので API には出さない

入力エラーは 400（項目ごとのメッセージ）。カラム名は claude/er-diagram.md に合わせる
"""
from rest_framework import serializers

from marche.models import Notification

from ...common.pagination import PageQuerySerializer
from ...common.serializers import QueryBooleanField, StrictSerializer


class NotificationListQuerySerializer(PageQuerySerializer):
    unread_only = QueryBooleanField(required=False, default=False)


class NotificationSerializer(serializers.ModelSerializer):
    is_read = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = ["id", "notification_type", "title", "body", "link_path", "is_read", "read_at", "created_at"]

    def get_is_read(self, notification):
        return notification.read_at is not None


class NotificationSettingSerializer(StrictSerializer):
    email_message = serializers.BooleanField()
    email_favorite = serializers.BooleanField()
    email_news = serializers.BooleanField()
