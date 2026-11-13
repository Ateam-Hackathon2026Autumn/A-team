"""操作ログ

認証: 管理者（権限グループ: 管理者）
仕様: api-spec.md「7. 実装で決めたこと」ステップ16（Notion には API の名前だけ）

実装済み:
  - 操作ログ一覧: GET /api/v1/admin/audit-logs
      ・adminId・action・targetType・targetId・startDate・endDate（日本時間の日付。両端を含む）で絞り込み。新しい順
      ・1件: {id, admin {id, name}, action, targetType, targetId, detail, createdAt}
"""
from datetime import datetime, time, timedelta

from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from marche.models import AuditLog

from ...common.pagination import paginate, validate_query
from ...common.permissions import AdminGroupPermission
from ...serializers.admin.settings import AuditLogQuerySerializer, AuditLogSerializer


def day_start(date):
    """日本時間（settings.TIME_ZONE）のその日の0時"""
    return timezone.make_aware(datetime.combine(date, time.min))


class AdminAuditLogListView(APIView):
    """GET /api/v1/admin/audit-logs"""

    permission_classes = [AdminGroupPermission]

    def get(self, request):
        query = validate_query(AuditLogQuerySerializer, request)
        logs = AuditLog.objects.all()
        for field in ("admin_id", "action", "target_type", "target_id"):
            if query.get(field) is not None:
                logs = logs.filter(**{field: query[field]})
        if query.get("start_date"):
            logs = logs.filter(created_at__gte=day_start(query["start_date"]))
        if query.get("end_date"):
            logs = logs.filter(created_at__lt=day_start(query["end_date"] + timedelta(days=1)))
        rows = logs.select_related("admin").order_by("-created_at", "-id")
        return Response(paginate(rows, query, AuditLogSerializer, count_queryset=logs))
