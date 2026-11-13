"""サイト内の通知・通知設定

認証: 会員（未ログインは 401）。メール未確認でも使える
仕様: api-spec.md「7. 実装で決めたこと」ステップ7b（Notion には名前だけ）。カラム名: claude/er-diagram.md

実装済み:
  - 通知一覧: GET /api/v1/notifications
      ・自分宛てを新しい順（created_at・id の降順）。unreadOnly=true で未読だけ
      ・ページングは共通の形に unreadCount（未読件数）を足す
  - 未読件数: GET /api/v1/notifications/unread-count → {unreadCount}（ヘッダーのバッジ用）
  - 既読にする: PATCH /api/v1/notifications/:notificationId/read
      ・200 で通知1件。既読の通知にもう一度呼んでもエラーにせず、最初に読んだ日時のまま
      ・他人の通知・存在しない通知は 404 NOTIFICATION_NOT_FOUND
  - すべて既読にする: POST /api/v1/notifications/read-all → {unreadCount: 0}
  - 通知設定: GET・PUT /api/v1/users/me/notification-settings
      ・{emailMessage, emailFavorite, emailNews}。PUT は3つとも必須でまるごと置き換え
      ・設定の行がない会員には、GET・PUT のときに初期値（すべて true）で作る
      ・取引のメール（注文確認・発送・キャンセル・返金など）は設定に関係なく必ず送る。設定を見て送り分けるのは
        新着メッセージ（チャット）・運営からのお知らせ・お気に入り生産者の新着（拡張）
"""
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from marche.models import Notification, NotificationSetting

from ...common.exceptions import ApiError
from ...common.pagination import paginate, validate_query
from ...serializers.public.notifications import (
    NotificationListQuerySerializer,
    NotificationSerializer,
    NotificationSettingSerializer,
)

MAX_ID = 2 ** 63 - 1


def unread_count(user):
    return Notification.objects.filter(user=user, read_at__isnull=True).count()


class NotificationListView(APIView):
    """GET /api/v1/notifications"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = validate_query(NotificationListQuerySerializer, request)
        notifications = Notification.objects.filter(user=request.user)
        if query["unread_only"]:
            notifications = notifications.filter(read_at__isnull=True)
        body = paginate(notifications.order_by("-created_at", "-id"), query, NotificationSerializer)
        body["unread_count"] = unread_count(request.user)
        return Response(body)


class NotificationUnreadCountView(APIView):
    """GET /api/v1/notifications/unread-count"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"unread_count": unread_count(request.user)})


class NotificationReadView(APIView):
    """PATCH /api/v1/notifications/:notificationId/read"""

    permission_classes = [IsAuthenticated]

    def patch(self, request, notification_id):
        notification = None
        if notification_id <= MAX_ID:
            notification = Notification.objects.filter(pk=notification_id, user=request.user).first()
        if notification is None:
            raise ApiError(status.HTTP_404_NOT_FOUND, "NOTIFICATION_NOT_FOUND", "通知が見つかりません。")
        if notification.read_at is None:
            Notification.objects.filter(pk=notification.pk, read_at__isnull=True).update(
                read_at=timezone.now(), updated_at=timezone.now())
            notification.refresh_from_db()
        return Response(NotificationSerializer(notification).data)


class NotificationReadAllView(APIView):
    """POST /api/v1/notifications/read-all"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        now = timezone.now()
        Notification.objects.filter(user=request.user, read_at__isnull=True).update(read_at=now, updated_at=now)
        return Response({"unread_count": 0})


class NotificationSettingView(APIView):
    """GET・PUT /api/v1/users/me/notification-settings"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        setting, _ = NotificationSetting.objects.get_or_create(user=request.user)
        return Response(NotificationSettingSerializer(setting).data)

    def put(self, request):
        serializer = NotificationSettingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        setting, _ = NotificationSetting.objects.get_or_create(user=request.user)
        for field, value in serializer.validated_data.items():
            setattr(setting, field, value)
        setting.save()
        return Response(NotificationSettingSerializer(setting).data)
