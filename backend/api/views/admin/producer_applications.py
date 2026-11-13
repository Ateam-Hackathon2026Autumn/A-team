"""生産者審査（管理者）

認証: 管理者（権限グループ: 審査担当・管理者。未ログイン 401、それ以外は 403）
共通: データを変える操作はすべて services/audit.py で audit_logs に記録する（target_type=producer_application）
仕様: api-spec.md「管理者：生産者審査」＋「7. 実装で決めたこと」（Notion には定義なし）。申請書類は扱わない

このファイルの API（シーケンス図は Notion の「生産者審査」）:
    - 申請一覧: GET /api/v1/admin/producer-applications
        ・status（初期値 pending）で絞り込み。pending は申請日の古い順、それ以外は新しい順。ページングは共通の形
    - 申請詳細: GET /api/v1/admin/producer-applications/:applicationId
        ・申請内容・生産者情報（画像URLも）・申請者（氏名・メール・電話）・同じ生産者の他の申請の履歴
    - 承認: POST /api/v1/admin/producer-applications/:applicationId/approve
        ・本文なし。producers を approved にし、approved_at は初めて承認したときだけ入れる（publish_status は draft のまま）
        ・空の producer_stories を作る。申請者に通知・メール（producer_review）
    - 却下: POST /api/v1/admin/producer-applications/:applicationId/reject
    - 差し戻し: POST /api/v1/admin/producer-applications/:applicationId/return
        ・{reviewComment}（必須・1,000文字まで）。producers.approval_status を rejected・returned に。申請者に通知・メール
    ・承認・却下・差し戻しは、その生産者の最新の申請で pending のものだけ（それ以外は 409 APPLICATION_NOT_PENDING）
    ・3つとも審査後の申請詳細を返す
"""
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from marche.models import Notification, Producer, ProducerApplication, ProducerStory

from ...common.exceptions import Conflict
from ...common.pagination import paginate, validate_query
from ...common.permissions import REVIEWER_GROUP, AdminGroupPermission
from ...common.serializers import QuerySerializer, StrictSerializer
from ...serializers.admin.producer_applications import (
    ApplicationDetailSerializer,
    ApplicationListItemSerializer,
    ApplicationListQuerySerializer,
    ReviewCommentSerializer,
)
from ...services.audit import record_audit_log
from ...services.notifications import PRODUCER_APPLICATION_PATH, notify

Status = ProducerApplication.Status
TARGET_TYPE = "producer_application"


class ReviewerView(APIView):
    permission_classes = [AdminGroupPermission]
    admin_groups = [REVIEWER_GROUP]


def detail_response(application_id):
    application = (ProducerApplication.objects
                   .select_related("producer__prefecture", "producer__user", "reviewer")
                   .filter(pk=application_id).first())
    if application is None:
        raise NotFound()
    application.history = list(ProducerApplication.objects.filter(producer_id=application.producer_id)
                               .exclude(pk=application.pk).order_by("-submitted_at", "-id"))
    return Response(ApplicationDetailSerializer(application).data)


class ApplicationListView(ReviewerView):
    """GET /api/v1/admin/producer-applications"""

    def get(self, request):
        query = validate_query(ApplicationListQuerySerializer, request)
        applications = ProducerApplication.objects.all()
        if query["status"] != "all":
            applications = applications.filter(status=query["status"])
        order = ["submitted_at", "id"] if query["status"] == Status.PENDING else ["-submitted_at", "-id"]
        listed = applications.select_related("producer__prefecture", "producer__user").order_by(*order)
        return Response(paginate(listed, query, ApplicationListItemSerializer, count_queryset=applications))


class ApplicationDetailView(ReviewerView):
    """GET /api/v1/admin/producer-applications/:applicationId"""

    def get(self, request, application_id):
        validate_query(QuerySerializer, request)  # クエリパラメーターは受け付けない
        with transaction.atomic():
            return detail_response(application_id)


class ReviewView(ReviewerView):
    """承認・却下・差し戻しの共通部分。サブクラスで result と notice を決める"""

    result = None  # Status.APPROVED / REJECTED / RETURNED

    def post(self, request, application_id):
        if self.result == Status.APPROVED:
            serializer = StrictSerializer(data=request.data or {})  # 本文は受け付けない
            serializer.is_valid(raise_exception=True)
            comment = None
        else:
            serializer = ReviewCommentSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            comment = serializer.validated_data["review_comment"]

        with transaction.atomic():
            application = ProducerApplication.objects.select_for_update().filter(pk=application_id).first()
            if application is None:
                raise NotFound()
            producer = Producer.objects.select_for_update().select_related("user").get(pk=application.producer_id)
            latest = (ProducerApplication.objects.filter(producer=producer)
                      .order_by("-submitted_at", "-id").values_list("pk", flat=True).first())
            if application.status != Status.PENDING or application.pk != latest:
                raise Conflict("APPLICATION_NOT_PENDING", "審査待ちの最新の申請だけ審査できます。")

            now = timezone.now()
            application.status = self.result
            application.review_comment = comment
            application.reviewer = request.user
            application.reviewed_at = now
            application.save(update_fields=["status", "review_comment", "reviewer", "reviewed_at", "updated_at"])

            producer.approval_status = self.result  # 申請の状態と同じ値（approved / rejected / returned）
            if self.result == Status.APPROVED:
                producer.approved_at = producer.approved_at or now  # 新規参加バッジは初めての承認から数える
                ProducerStory.objects.get_or_create(producer=producer)
            producer.save(update_fields=["approval_status", "approved_at", "updated_at"])

            record_audit_log(admin=request.user, action=self.action_name, target_type=TARGET_TYPE,
                             target_id=application.pk, detail={"producer_id": producer.pk, "review_comment": comment})
            title, body = self.notice(producer, comment)
            notify(producer.user, Notification.NotificationType.PRODUCER_REVIEW, title=title, body=body,
                   link_path=PRODUCER_APPLICATION_PATH)
            return detail_response(application.pk)

    @property
    def action_name(self):
        return {Status.APPROVED: "approve", Status.REJECTED: "reject", Status.RETURNED: "return"}[self.result]


class ApproveView(ReviewView):
    """POST /api/v1/admin/producer-applications/:applicationId/approve"""

    result = Status.APPROVED

    def notice(self, producer, comment):
        return ("生産者登録が承認されました", (
            f"{producer.business_name}の生産者登録が承認されました。\n"
            "生産者ダッシュボードから、配送設定・商品・プロフィールを登録してください。"
            "準備ができたら、プロフィールを公開すると購入者に表示されます。\n"))


class RejectView(ReviewView):
    """POST /api/v1/admin/producer-applications/:applicationId/reject"""

    result = Status.REJECTED

    def notice(self, producer, comment):
        return ("生産者登録の審査結果のお知らせ", (
            f"{producer.business_name}の生産者登録は、審査の結果、承認されませんでした。\n"
            f"理由: {comment}\n"
            "内容を見直して、申請状況の画面から再申請することができます。\n"))


class ReturnView(ReviewView):
    """POST /api/v1/admin/producer-applications/:applicationId/return"""

    result = Status.RETURNED

    def notice(self, producer, comment):
        return ("生産者登録の申請内容の修正をお願いします", (
            f"{producer.business_name}の生産者登録の申請について、修正をお願いします。\n"
            f"修正していただきたい点: {comment}\n"
            "申請状況の画面から内容を修正して、再申請してください。\n"))
