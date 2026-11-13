"""運営からのお知らせ（notices テーブル）

認証: 公開（生産者向けだけ承認済みの生産者のログインが必要）
仕様: api-spec.md「7. 実装で決めたこと」ステップ7b（Notion には名前だけ）。カラム名: claude/er-diagram.md

実装済み:
  - お知らせ一覧: GET /api/v1/announcements
      ・公開日時（published_at）が現在以前のものだけ。published_at・id の降順。ページングは共通の形
      ・audience を省略（consumer）: 全員向け（all）と消費者向け（consumer）
      ・audience=producer: 全員向けと生産者向け。承認済みの生産者だけ（未ログインは 401、生産者でなければ 403）。
        掲載停止中の生産者も見られる
      ・1件は {id, title, audience, publishedAt}（本文は詳細で）
  - お知らせ詳細: GET /api/v1/announcements/:announcementId
      ・一覧の項目＋body。公開前・存在しないものは 404 ANNOUNCEMENT_NOT_FOUND
      ・生産者向けのお知らせは、承認済みの生産者以外には 404
  - お知らせには既読・未読を持たせない（サイト内の通知とは別物）
"""
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import NotAuthenticated
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from marche.models import Notice, Producer

from ...common.exceptions import ApiError
from ...common.pagination import paginate, validate_query
from ...serializers.public.announcements import (
    AnnouncementDetailSerializer,
    AnnouncementListQuerySerializer,
    AnnouncementSerializer,
)

MAX_ID = 2 ** 63 - 1
Audience = Notice.Audience


def is_approved_producer(user):
    return user.is_authenticated and Producer.objects.filter(
        user=user, approval_status=Producer.ApprovalStatus.APPROVED).exists()


def published_notices():
    return Notice.objects.filter(published_at__lte=timezone.now())


class AnnouncementListView(APIView):
    """GET /api/v1/announcements"""

    permission_classes = [AllowAny]

    def get(self, request):
        query = validate_query(AnnouncementListQuerySerializer, request)
        audiences = [Audience.ALL, Audience.CONSUMER]
        if query["audience"] == "producer":
            if not request.user.is_authenticated:
                raise NotAuthenticated()
            if not is_approved_producer(request.user):
                raise ApiError(status.HTTP_403_FORBIDDEN, "FORBIDDEN", "生産者向けのお知らせは生産者だけが見られます。")
            audiences = [Audience.ALL, Audience.PRODUCER]
        notices = published_notices().filter(audience__in=audiences).order_by("-published_at", "-id")
        return Response(paginate(notices, query, AnnouncementSerializer))


class AnnouncementDetailView(APIView):
    """GET /api/v1/announcements/:announcementId"""

    permission_classes = [AllowAny]

    def get(self, request, announcement_id):
        notice = published_notices().filter(pk=announcement_id).first() if announcement_id <= MAX_ID else None
        if notice is None or (notice.audience == Audience.PRODUCER and not is_approved_producer(request.user)):
            raise ApiError(status.HTTP_404_NOT_FOUND, "ANNOUNCEMENT_NOT_FOUND", "お知らせが見つかりません。")
        return Response(AnnouncementDetailSerializer(notice).data)
