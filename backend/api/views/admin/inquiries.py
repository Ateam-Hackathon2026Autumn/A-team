"""問い合わせ対応

認証: 管理者（権限グループ: CS・管理者）
仕様: api-spec.md「7. 実装で決めたこと」ステップ15（Notion には API の名前だけ）

実装済み:
  - 問い合わせ一覧: GET /api/v1/admin/inquiries
      ・status（カンマ区切り。初期値 open,in_progress）・priority・category・assigneeId（数字か me）・
        keyword（受付番号・件名・メール）。優先度の高い順 → 古い順
  - 問い合わせ詳細: GET /api/v1/admin/inquiries/:inquiryId
      ・本文・user {id, name}・order {id, orderNo}・notes（対応メモ。古い順）
  - 問い合わせ更新: PATCH /api/v1/admin/inquiries/:inquiryId {status, priority, assigneeId, note}（1つ以上）
      ・assigneeId は CS・管理者のスタッフか null（担当を外す）。note は inquiry_notes に追加（2,000文字まで）
      ・閉じた問い合わせも open に戻せる。お客さんへのメールは送らない（返信はメールソフトで行う）
      ・操作ログ（action=update、target_type=inquiry、detail {before, after, noteAdded}）。200 で詳細
"""
from django.db import transaction
from django.db.models import Case, IntegerField, Prefetch, Q, Value, When
from rest_framework import serializers
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from marche.models import Inquiry, InquiryNote, User

from ...common.pagination import paginate, validate_query
from ...common.permissions import ADMIN_GROUP, CS_GROUP, AdminGroupPermission
from ...common.serializers import QuerySerializer
from ...serializers.admin.inquiries import (DEFAULT_STATUSES, MAX_ID, AdminInquiryDetailSerializer,
                                            AdminInquiryListItemSerializer, InquiryListQuerySerializer,
                                            InquiryUpdateSerializer)
from ...services.audit import record_audit_log

PRIORITY_ORDER = Case(
    When(priority=Inquiry.Priority.HIGH, then=Value(0)),
    When(priority=Inquiry.Priority.MEDIUM, then=Value(1)),
    default=Value(2), output_field=IntegerField())
TRACKED = ["status", "priority", "assignee_id"]


def load_detail(inquiry_id):
    notes = InquiryNote.objects.select_related("author").order_by("created_at", "id")
    inquiry = (Inquiry.objects.select_related("assignee", "user", "order")
               .prefetch_related(Prefetch("inquiry_notes", queryset=notes)).filter(pk=inquiry_id).first()
               if inquiry_id <= MAX_ID else None)
    if inquiry is None:
        raise NotFound()
    return inquiry


class AdminInquiryListView(APIView):
    """GET /api/v1/admin/inquiries"""

    permission_classes = [AdminGroupPermission]
    admin_groups = [CS_GROUP]

    def get(self, request):
        query = validate_query(InquiryListQuerySerializer, request)
        inquiries = Inquiry.objects.filter(status__in=query.get("status") or DEFAULT_STATUSES)
        for field in ("priority", "category"):
            if query.get(field):
                inquiries = inquiries.filter(**{field: query[field]})
        assignee = query.get("assignee_id")
        if assignee is not None:
            inquiries = inquiries.filter(assignee_id=request.user.pk if assignee == "me" else assignee)
        keyword = (query.get("keyword") or "").strip()
        if keyword:
            condition = Q(subject__icontains=keyword) | Q(email__icontains=keyword)
            if keyword.isdigit() and int(keyword) <= MAX_ID:
                condition |= Q(pk=int(keyword))
            inquiries = inquiries.filter(condition)
        rows = (inquiries.select_related("assignee").annotate(priority_order=PRIORITY_ORDER)
                .order_by("priority_order", "created_at", "id"))
        return Response(paginate(rows, query, AdminInquiryListItemSerializer, count_queryset=inquiries))


class AdminInquiryDetailView(APIView):
    """GET・PATCH /api/v1/admin/inquiries/:inquiryId"""

    permission_classes = [AdminGroupPermission]
    admin_groups = [CS_GROUP]

    def get(self, request, inquiry_id):
        validate_query(QuerySerializer, request)
        return Response(AdminInquiryDetailSerializer(load_detail(inquiry_id)).data)

    def patch(self, request, inquiry_id):
        serializer = InquiryUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if data.get("assignee_id") is not None:
            is_staff_member = User.objects.filter(
                pk=data["assignee_id"], is_staff=True, is_active=True,
                groups__name__in=[CS_GROUP, ADMIN_GROUP]).exists()
            if not is_staff_member:
                raise serializers.ValidationError({"assignee_id": ["CS か管理者のスタッフを選んでください。"]})
        with transaction.atomic():
            inquiry = Inquiry.objects.select_for_update().filter(pk=inquiry_id).first() if inquiry_id <= MAX_ID else None
            if inquiry is None:
                raise NotFound()
            before = {field: getattr(inquiry, field) for field in TRACKED}
            changed = [field for field in TRACKED if field in data]
            for field in changed:
                setattr(inquiry, field, data[field])
            inquiry.save(update_fields=changed + ["updated_at"])  # メモだけでも updated_at を進める
            if data.get("note"):
                InquiryNote.objects.create(inquiry=inquiry, author=request.user, body=data["note"])
            record_audit_log(admin=request.user, action="update", target_type="inquiry", target_id=inquiry.pk,
                             detail={"before": before, "after": {f: getattr(inquiry, f) for f in TRACKED},
                                     "note_added": bool(data.get("note"))})
        return Response(AdminInquiryDetailSerializer(load_detail(inquiry.pk)).data)
