"""生産者・商品・体験・求人・ストーリーの管理（掲載停止・再開）

認証: 管理者（権限グループ: 審査担当・管理者）
仕様: api-spec.md「7. 実装で決めたこと」ステップ14（Notion にはシーケンス図「管理者の〇〇管理」と名前だけ）

実装済み（resource = producers・products・experiences・jobs・stories。RESOURCES に種類ごとの違いをまとめた）:
  - 一覧: GET /api/v1/admin/{resource}
      ・keyword（生産者は事業者名・代表者名・メール、商品は名前、体験・求人はタイトル、ストーリーは事業者名）・
        publishStatus・producerId（生産者以外）で絞り込み。下書きや停止中も出す。updated_at・id の新しい順。共通のページング
      ・生産者は承認済みだけ（審査中などは生産者審査の画面）
  - 詳細: GET /api/v1/admin/{resource}/:id（stories の :id は producer_stories.id）
      ・その行の全項目＋画像 URL＋producer。掲載停止中なら suspension {reason, suspendedAt, suspendedBy}（操作ログの最新の停止）
      ・体験は upcomingReservationCount（これからの確定済み予約）、求人は openApplicationCount（応募済み・選考中）、
        生産者は counts（商品・体験・求人の数）と storyId
  - 掲載停止・再開: PATCH /api/v1/admin/{resource}/:id/status {action, reason}
      ・suspend: reason 必須。publish_status=suspended。停止中なら 409 STATUS_CONFLICT
      ・resume: reason 任意。private に戻す（生産者が確認してから自分で公開）。停止中でなければ 409 STATUS_CONFLICT
        生産者の resume は、ログインアカウントが利用停止・退会なら 409 USER_INACTIVE
      ・生産者を止めても商品などの状態は変えない（公開側からは services/visibility.py の条件で消える）
      ・すでに入っている注文・予約・応募は自動でキャンセルしない
      ・生産者に通知とメール（listing_suspended・listing_resumed。利用中のアカウントだけ）。操作ログ（action・
        target_type・detail {reason, before, after}）。200 で更新後の詳細
"""
from django.db import transaction
from django.db.models import Count, IntegerField, OuterRef, Prefetch, Q, Subquery, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from marche.models import (AuditLog, Experience, ExperienceImage, Job, JobApplication, JobWorkDate, Notification,
                           Producer, ProducerImage, ProducerStory, Product, ProductImage, PublishStatus, Reservation)

from ...common.exceptions import Conflict
from ...common.pagination import paginate, validate_query
from ...common.permissions import REVIEWER_GROUP, AdminGroupPermission
from ...common.serializers import QuerySerializer
from ...serializers.admin import contents as s
from ...services.audit import record_audit_log
from ...services.notifications import notify

MAX_ID = 2 ** 63 - 1
SUSPEND = "suspend"
RESUME = "resume"


class Resource:
    """種類ごとの違い"""

    def __init__(self, model, target_type, label, keyword_fields, list_serializer, detail_serializer,
                 list_related, link_path, name_field="title", query_serializer=s.ContentListQuerySerializer):
        self.model = model
        self.target_type = target_type
        self.label = label
        self.keyword_fields = keyword_fields
        self.list_serializer = list_serializer
        self.detail_serializer = detail_serializer
        self.list_related = list_related
        self.link_path = link_path
        self.name_field = name_field
        self.query_serializer = query_serializer

    def base_queryset(self):
        queryset = self.model.objects.all()
        if self.model is Producer:
            queryset = queryset.filter(approval_status=Producer.ApprovalStatus.APPROVED)
        return queryset

    def owner(self, obj):
        """通知を送る生産者"""
        return obj if self.model is Producer else obj.producer

    def display_name(self, obj):
        if self.model is Producer:
            return f"農園「{obj.business_name}」"
        if self.model is ProducerStory:
            return "学ぶページのストーリー"
        return f"{self.label}「{getattr(obj, self.name_field)}」"

    def detail_queryset(self):
        """詳細で使う select_related・prefetch・集計"""
        queryset = self.base_queryset().select_related(*self.list_related)
        now = timezone.now()
        if self.model is Producer:
            images = ProducerImage.objects.order_by("sort_order", "id")
            return queryset.select_related("story").prefetch_related(Prefetch("producer_images", queryset=images))
        if self.model is Product:
            images = ProductImage.objects.order_by("sort_order", "id")
            return queryset.prefetch_related(Prefetch("product_images", queryset=images))
        if self.model is Experience:
            images = ExperienceImage.objects.order_by("sort_order", "id")
            upcoming = Reservation.objects.filter(slot__experience=OuterRef("pk"), status=Reservation.Status.CONFIRMED,
                                                  slot__start_at__gte=now)
            return queryset.prefetch_related(Prefetch("experience_images", queryset=images)).annotate(
                upcoming_reservation_count=count_subquery(upcoming, "slot__experience"))
        if self.model is Job:
            dates = JobWorkDate.objects.order_by("work_date", "id")
            open_applications = JobApplication.objects.filter(
                job=OuterRef("pk"), status__in=[JobApplication.Status.APPLIED, JobApplication.Status.SCREENING])
            return queryset.prefetch_related(Prefetch("job_work_dates", queryset=dates)).annotate(
                open_application_count=count_subquery(open_applications, "job"))
        return queryset


def count_subquery(queryset, group_field):
    """件数のサブクエリ（なければ0）"""
    counted = queryset.order_by().values(group_field).annotate(c=Count("id")).values("c")[:1]
    return Coalesce(Subquery(counted, output_field=IntegerField()), Value(0))


RESOURCES = {
    "producers": Resource(
        Producer, "producer", "農園", ["business_name", "representative_name", "user__email"],
        s.ProducerListItemSerializer, s.ProducerDetailSerializer, ["prefecture", "user"], "/dashboard",
        name_field="business_name", query_serializer=s.ProducerListQuerySerializer),
    "products": Resource(
        Product, "product", "商品", ["name"], s.ProductListItemSerializer, s.ProductDetailSerializer,
        ["producer__user", "category"], "/dashboard/products/{id}", name_field="name"),
    "experiences": Resource(
        Experience, "experience", "体験", ["title"], s.ExperienceListItemSerializer, s.ExperienceDetailSerializer,
        ["producer__user", "prefecture"], "/dashboard/experiences/{id}"),
    "jobs": Resource(
        Job, "job", "求人", ["title"], s.JobListItemSerializer, s.JobDetailSerializer,
        ["producer__user", "prefecture"], "/dashboard/jobs/{id}"),
    "stories": Resource(
        ProducerStory, "producer_story", "ストーリー", ["producer__business_name"], s.StoryListItemSerializer,
        s.StoryDetailSerializer, ["producer__user"], "/dashboard/story"),
}


def find_detail(resource, obj_id):
    if obj_id > MAX_ID:
        raise NotFound()
    obj = resource.detail_queryset().filter(pk=obj_id).first()
    if obj is None:
        raise NotFound()
    if resource.model is Producer:
        obj.content_counts = {
            "products": Product.objects.filter(producer=obj).count(),
            "experiences": Experience.objects.filter(producer=obj).count(),
            "jobs": Job.objects.filter(producer=obj).count(),
        }
    obj.suspension = suspension_of(resource, obj)
    return obj


def suspension_of(resource, obj):
    """掲載停止中なら、操作ログの最新の停止 {reason, suspendedAt, suspendedBy}。ほかは None"""
    if obj.publish_status != PublishStatus.SUSPENDED:
        return None
    log = (AuditLog.objects.filter(target_type=resource.target_type, target_id=obj.pk, action=SUSPEND)
           .select_related("admin").order_by("-created_at", "-id").first())
    if log is None:  # 退会・利用停止で自動的に suspended になった生産者など
        return {"reason": None, "suspended_at": None, "suspended_by": None}
    admin = log.admin
    return {"reason": (log.detail or {}).get("reason"), "suspended_at": log.created_at,
            "suspended_by": {"id": admin.pk, "name": f"{admin.last_name} {admin.first_name}".strip()}}


class ContentView(APIView):
    """as_view(resource="products") のように種類を渡して使う"""

    permission_classes = [AdminGroupPermission]
    admin_groups = [REVIEWER_GROUP]
    resource = None

    @property
    def config(self):
        return RESOURCES[self.resource]


class ContentListView(ContentView):
    """GET /api/v1/admin/{resource}"""

    def get(self, request):
        config = self.config
        query = validate_query(config.query_serializer, request)
        queryset = config.base_queryset()
        keyword = (query.get("keyword") or "").strip()
        if keyword:
            condition = Q()
            for field in config.keyword_fields:
                condition |= Q(**{f"{field}__icontains": keyword})
            queryset = queryset.filter(condition)
        if query.get("publish_status"):
            queryset = queryset.filter(publish_status=query["publish_status"])
        if query.get("producer_id"):
            queryset = queryset.filter(producer_id=query["producer_id"])
        rows = queryset.select_related(*config.list_related).order_by("-updated_at", "-id")
        return Response(paginate(rows, query, config.list_serializer, count_queryset=queryset))


class ContentDetailView(ContentView):
    """GET /api/v1/admin/{resource}/:id"""

    def get(self, request, obj_id):
        validate_query(QuerySerializer, request)
        return Response(self.config.detail_serializer(find_detail(self.config, obj_id)).data)


class ContentStatusView(ContentView):
    """PATCH /api/v1/admin/{resource}/:id/status"""

    def patch(self, request, obj_id):
        config = self.config
        serializer = s.StatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        action, reason = serializer.validated_data["action"], serializer.validated_data["reason"]
        if obj_id > MAX_ID:
            raise NotFound()
        with transaction.atomic():
            obj = (config.base_queryset().select_for_update().select_related(*config.list_related)
                   .filter(pk=obj_id).first())
            if obj is None:
                raise NotFound()
            before = obj.publish_status
            if action == SUSPEND and before == PublishStatus.SUSPENDED:
                raise Conflict("STATUS_CONFLICT", "すでに掲載停止中です。")
            if action == RESUME and before != PublishStatus.SUSPENDED:
                raise Conflict("STATUS_CONFLICT", "掲載停止中ではありません。")
            owner = config.owner(obj)
            owner_active = owner.user.is_active and owner.user.deleted_at is None
            if action == RESUME and config.model is Producer and not owner_active:
                raise Conflict("USER_INACTIVE", "ログインアカウントが利用停止中または退会済みのため、再開できません。")

            obj.publish_status = PublishStatus.SUSPENDED if action == SUSPEND else PublishStatus.PRIVATE
            obj.save(update_fields=["publish_status", "updated_at"])
            record_audit_log(admin=request.user, action=action, target_type=config.target_type, target_id=obj.pk,
                             detail={"reason": reason, "before": before, "after": obj.publish_status})
            if owner_active:
                self.notify_owner(config, obj, owner, action, reason)
        return Response(config.detail_serializer(find_detail(config, obj.pk)).data)

    @staticmethod
    def notify_owner(config, obj, owner, action, reason):
        name = config.display_name(obj)
        link = config.link_path.format(id=obj.pk)
        if action == SUSPEND:
            notify(owner.user, Notification.NotificationType.LISTING_SUSPENDED, f"{name}の掲載を停止しました",
                   f"運営の判断により、{name}の掲載を停止しました。お客様の画面には表示されません。\n\n"
                   f"理由：\n{reason}\n\nご不明な点は、お問い合わせフォームからご連絡ください。\n", link)
        else:
            notify(owner.user, Notification.NotificationType.LISTING_RESUMED, f"{name}の掲載停止を解除しました",
                   f"{name}の掲載停止を解除しました。今は非公開になっています。\n"
                   "内容を確認のうえ、管理画面から公開してください。\n"
                   + (f"\n運営からのコメント：\n{reason}\n" if reason else ""), link)
