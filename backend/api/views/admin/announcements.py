"""お知らせ管理（notices テーブル）

認証: 管理者（権限グループ: 管理者）
仕様: api-spec.md「7. 実装で決めたこと」ステップ16（Notion には API の名前だけ）

実装済み:
  - お知らせ一覧（管理者）: GET /api/v1/admin/announcements
      ・status（draft＝published_at が空・scheduled＝未来・published＝過去）・audience・keyword（タイトル）。更新日時の新しい順
  - お知らせ詳細（管理者）: GET /api/v1/admin/announcements/:announcementId（編集画面用に追加。一覧の項目＋body）
  - お知らせ作成: POST /api/v1/admin/announcements {title, body, audience, publishedAt}
      ・publishedAt が null なら下書き。過去の日時ならすぐ公開。201
  - お知らせ更新: PATCH /api/v1/admin/announcements/:announcementId（送った項目だけ）
  - お知らせ削除: DELETE /api/v1/admin/announcements/:announcementId（物理削除。204）
  - 作成・更新・削除は操作ログ（target_type=notice）。利用者への通知は送らない（公開側の GET /announcements で見る）
"""
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from marche.models import Notice

from ...common.pagination import paginate, validate_query
from ...common.permissions import AdminGroupPermission
from ...common.serializers import QuerySerializer
from ...serializers.admin.settings import (DRAFT, MAX_ID, PUBLISHED, SCHEDULED, AdminAnnouncementDetailSerializer,
                                           AdminAnnouncementSerializer, AnnouncementListQuerySerializer,
                                           AnnouncementWriteSerializer)
from ...services.audit import record_audit_log

FIELDS = ["title", "body", "audience", "published_at"]


def snapshot(notice):
    """操作ログに残す値（本文は長いので残さない）"""
    return {"title": notice.title, "audience": notice.audience,
            "published_at": notice.published_at.isoformat() if notice.published_at else None}


def get_notice(notice_id, lock=False):
    notices = Notice.objects.select_for_update() if lock else Notice.objects.all()
    notice = notices.filter(pk=notice_id).first() if notice_id <= MAX_ID else None
    if notice is None:
        raise NotFound()
    return notice


class AdminAnnouncementListView(APIView):
    """GET・POST /api/v1/admin/announcements"""

    permission_classes = [AdminGroupPermission]

    def get(self, request):
        query = validate_query(AnnouncementListQuerySerializer, request)
        notices = Notice.objects.all()
        now = timezone.now()
        state = query.get("status")
        if state == DRAFT:
            notices = notices.filter(published_at__isnull=True)
        elif state == SCHEDULED:
            notices = notices.filter(published_at__gt=now)
        elif state == PUBLISHED:
            notices = notices.filter(published_at__lte=now)
        if query.get("audience"):
            notices = notices.filter(audience=query["audience"])
        keyword = (query.get("keyword") or "").strip()
        if keyword:
            notices = notices.filter(title__icontains=keyword)
        return Response(paginate(notices.order_by("-updated_at", "-id"), query, AdminAnnouncementSerializer))

    def post(self, request):
        serializer = AnnouncementWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            notice = Notice.objects.create(**serializer.validated_data)
            record_audit_log(admin=request.user, action="create", target_type="notice", target_id=notice.pk,
                             detail={"after": snapshot(notice)})
        return Response(AdminAnnouncementDetailSerializer(notice).data, status=status.HTTP_201_CREATED)


class AdminAnnouncementDetailView(APIView):
    """GET・PATCH・DELETE /api/v1/admin/announcements/:announcementId"""

    permission_classes = [AdminGroupPermission]

    def get(self, request, announcement_id):
        validate_query(QuerySerializer, request)
        return Response(AdminAnnouncementDetailSerializer(get_notice(announcement_id)).data)

    def patch(self, request, announcement_id):
        serializer = AnnouncementWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            notice = get_notice(announcement_id, lock=True)
            before = snapshot(notice)
            for field, value in serializer.validated_data.items():
                setattr(notice, field, value)
            notice.save()
            record_audit_log(admin=request.user, action="update", target_type="notice", target_id=notice.pk,
                             detail={"before": before, "after": snapshot(notice)})
        return Response(AdminAnnouncementDetailSerializer(notice).data)

    def delete(self, request, announcement_id):
        with transaction.atomic():
            notice = get_notice(announcement_id, lock=True)
            record_audit_log(admin=request.user, action="delete", target_type="notice", target_id=notice.pk,
                             detail={"before": snapshot(notice)})
            notice.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
