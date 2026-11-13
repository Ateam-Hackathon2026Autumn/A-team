"""通報対応

認証: 管理者（権限グループ: CS・管理者）
仕様: api-spec.md「7. 実装で決めたこと」ステップ15（Notion には API の名前だけ）

実装済み:
  - 通報一覧: GET /api/v1/admin/reports
      ・status（初期値 open）・targetType で絞り込み。古い順
      ・1件: {id, targetType, targetId, target {name, publishStatus, adminPath}（対象が消えていれば null）, reason,
        reasonLabel, detail, reporter {id, name, email}, status, handledBy, sameTargetCount（同じ対象への未対応の通報の数）,
        createdAt, updatedAt}
  - 通報の対応更新: PATCH /api/v1/admin/reports/:reportId {status}
      ・open・resolved・dismissed。resolved・dismissed なら handled_by を自分に、open に戻したら空に
      ・掲載停止はここではせず、掲載の管理の API（contents.py）で行う。通報した人へのメールはなし
      ・操作ログ（action=update、target_type=report）。200 で1件
"""
from django.db import transaction
from django.db.models import Count, IntegerField, OuterRef, Subquery, Value
from django.db.models.functions import Coalesce
from rest_framework import serializers
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from marche.models import Experience, Job, Producer, Product, Report, User

from ...common.pagination import PageQuerySerializer, paginate, validate_query
from ...common.permissions import CS_GROUP, AdminGroupPermission
from ...common.serializers import StrictSerializer
from ...serializers.public.reports import REPORT_REASONS
from ...services.audit import record_audit_log

MAX_ID = 2 ** 63 - 1

# 対象の種類 → (モデル, 名前の項目, 管理画面のパス)
TARGETS = {
    Report.TargetType.PRODUCT: (Product, "name", "/admin/products/{id}"),
    Report.TargetType.EXPERIENCE: (Experience, "title", "/admin/experiences/{id}"),
    Report.TargetType.JOB: (Job, "title", "/admin/jobs/{id}"),
    Report.TargetType.PRODUCER: (Producer, "business_name", "/admin/producers/{id}"),
    Report.TargetType.USER: (User, None, "/admin/users/{id}"),
}


class ReportListQuerySerializer(PageQuerySerializer):
    status = serializers.ChoiceField(choices=Report.Status.choices, required=False)
    target_type = serializers.ChoiceField(choices=Report.TargetType.choices, required=False)


class ReportUpdateSerializer(StrictSerializer):
    status = serializers.ChoiceField(choices=Report.Status.choices)


def person(user):
    if user is None:
        return None
    return {"id": user.pk, "name": f"{user.last_name} {user.first_name}".strip()}


def describe_targets(reports):
    """通報の対象の {name, publishStatus, adminPath} を種類ごとに1回の SQL で読む"""
    ids = {}
    for report in reports:
        ids.setdefault(report.target_type, set()).add(report.target_id)
    found = {}
    for target_type, target_ids in ids.items():
        if target_type not in TARGETS:  # story（拡張のストーリー記事）
            continue
        model, name_field, path = TARGETS[target_type]
        for obj in model.objects.filter(pk__in=[i for i in target_ids if i <= MAX_ID]):
            if model is User:
                name, publish_status = f"{obj.last_name} {obj.first_name}".strip(), None
            else:
                name, publish_status = getattr(obj, name_field), obj.publish_status
            found[(target_type, obj.pk)] = {"name": name, "publish_status": publish_status,
                                            "admin_path": path.format(id=obj.pk)}
    return found


def serialize(report, targets):
    return {
        "id": report.id, "target_type": report.target_type, "target_id": report.target_id,
        "target": targets.get((report.target_type, report.target_id)), "reason": report.reason,
        "reason_label": REPORT_REASONS.get(report.reason, report.reason), "detail": report.detail,
        "reporter": {**person(report.reporter), "email": report.reporter.email},
        "status": report.status, "handled_by": person(report.handled_by),
        "same_target_count": report.same_target_count,
        "created_at": report.created_at, "updated_at": report.updated_at,
    }


def with_same_target_count(queryset):
    same = (Report.objects.filter(target_type=OuterRef("target_type"), target_id=OuterRef("target_id"),
                                  status=Report.Status.OPEN)
            .order_by().values("target_type").annotate(c=Count("id")).values("c")[:1])
    return queryset.annotate(same_target_count=Coalesce(Subquery(same, output_field=IntegerField()), Value(0)))


class _Collector(serializers.BaseSerializer):
    """paginate の中ではモデルのまま返す（対象をまとめて読んでから serialize で形を作るため）"""

    def to_representation(self, report):
        return report


class AdminReportListView(APIView):
    """GET /api/v1/admin/reports"""

    permission_classes = [AdminGroupPermission]
    admin_groups = [CS_GROUP]

    def get(self, request):
        query = validate_query(ReportListQuerySerializer, request)
        reports = Report.objects.filter(status=query.get("status") or Report.Status.OPEN)
        if query.get("target_type"):
            reports = reports.filter(target_type=query["target_type"])
        rows = with_same_target_count(reports.select_related("reporter", "handled_by")).order_by("created_at", "id")
        page = paginate(rows, query, _Collector, count_queryset=reports)
        targets = describe_targets(page["items"])
        page["items"] = [serialize(report, targets) for report in page["items"]]
        return Response(page)


class AdminReportDetailView(APIView):
    """PATCH /api/v1/admin/reports/:reportId"""

    permission_classes = [AdminGroupPermission]
    admin_groups = [CS_GROUP]

    def patch(self, request, report_id):
        serializer = ReportUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data["status"]
        with transaction.atomic():
            report = Report.objects.select_for_update().filter(pk=report_id).first() if report_id <= MAX_ID else None
            if report is None:
                raise NotFound()
            before = report.status
            report.status = new_status
            report.handled_by = None if new_status == Report.Status.OPEN else request.user
            report.save(update_fields=["status", "handled_by", "updated_at"])
            record_audit_log(admin=request.user, action="update", target_type="report", target_id=report.pk,
                             detail={"before": before, "after": new_status})
        report = with_same_target_count(Report.objects.select_related("reporter", "handled_by")).get(pk=report.pk)
        return Response(serialize(report, describe_targets([report])))
