"""体験管理・予約枠・申込者（生産者ダッシュボード）

認証: 承認済みの生産者（IsApprovedProducer。未ログイン 401、生産者でない・承認前は 403）
掲載停止中の生産者: 閲覧と予約枠の「中止」だけできる。登録・更新・削除は 409 PRODUCER_SUSPENDED
他の生産者の体験・別の体験の予約枠は 404（存在を隠す）

このファイルの API（シーケンス図は Notion の同名の図）:
    - 体験一覧（生産者）: GET    /api/v1/dashboard/experiences
    - 体験登録:           POST   /api/v1/dashboard/experiences
        ・prefectureId 省略時は生産者の都道府県。公開には画像1枚以上（409 IMAGE_REQUIRED）
    - 体験詳細（生産者）: GET    /api/v1/dashboard/experiences/:experienceId
    - 体験更新:           PATCH  /api/v1/dashboard/experiences/:experienceId
        ・料金を変えても既存予約の total_amount は変えない
        ・運営に掲載停止された体験は、内容の編集は可、publishStatus の変更は 409 CONTENT_SUSPENDED
    - 体験削除:           DELETE /api/v1/dashboard/experiences/:experienceId
        ・予約されたことがあれば 409 HAS_RESERVATIONS（非公開にしてもらう）。成功は 204
    - 体験申込者一覧:     GET    /api/v1/dashboard/experiences/:experienceId/applications
    - 予約枠一覧:         GET    /api/v1/dashboard/experiences/:experienceId/slots
    - 予約枠登録:         POST   /api/v1/dashboard/experiences/:experienceId/slots
        ・1件ずつ。startAt は未来。同じ開始日時の枠は 409 DUPLICATE_SLOT
    - 予約枠更新・中止:   PATCH  /api/v1/dashboard/experiences/:experienceId/slots/:slotId
        ・過去・中止済みは 409 SLOT_NOT_EDITABLE
        ・予約があれば startAt・durationMin は変更不可（409 SLOT_TIME_LOCKED。同じ値は可）
        ・capacity は reserved_count 以上（409 CAPACITY_BELOW_RESERVED）
        ・canceled（中止）にすると申込済み・確定済みの予約を全キャンセルし、予約者に通知とメール
            （元に戻せない。生産者が掲載停止中でも中止はできる）
    - 予約枠削除:         DELETE /api/v1/dashboard/experiences/:experienceId/slots/:slotId
        ・過去は 409 SLOT_NOT_EDITABLE、予約されたことがあれば 409 HAS_RESERVATIONS（中止にしてもらう）。成功は 204

同時実行: 更新・削除は体験 → 予約枠 → 予約の順に select_for_update でロックしてから確かめる
（予約申込API も同じ順でロックする）。
"""
from django.db import transaction
from django.db.models import Count, Min, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from marche.models import Experience, ExperienceSlot, Notification, PublishStatus, Reservation

from ...common.exceptions import Conflict
from ...common.pagination import paginate, validate_query
from ...common.permissions import IsApprovedProducer, ensure_producer_not_suspended
from ...serializers.dashboard.experiences import (
    ApplicationQuerySerializer,
    ApplicationSerializer,
    ExperienceDetailSerializer,
    ExperienceListQuerySerializer,
    ExperienceSummarySerializer,
    ExperienceWriteResponseSerializer,
    ExperienceWriteSerializer,
    SlotCreateSerializer,
    SlotQuerySerializer,
    SlotSerializer,
    SlotUpdateSerializer,
)
from ...services.notifications import notify

# 予約枠の中止で取り消す予約の状態（attended・canceled は対象外）
ACTIVE_RESERVATION_STATUSES = [Reservation.Status.APPLIED, Reservation.Status.CONFIRMED]


class ProducerExperienceView(APIView):
    """体験管理APIの共通部分"""

    permission_classes = [IsApprovedProducer]

    @property
    def producer(self):
        return self.request.user.producer

    def get_experience(self, experience_id, lock=False):
        """自分の体験を1件取る。他の生産者の体験・存在しない ID は 404"""
        queryset = Experience.objects.filter(producer=self.producer)
        if lock:
            queryset = queryset.select_for_update()
        return get_object_or_404(queryset, pk=experience_id)

    def get_slot(self, experience, slot_id, lock=False):
        """その体験の予約枠を1件取る。別の体験の枠は 404"""
        queryset = ExperienceSlot.objects.filter(experience=experience)
        if lock:
            queryset = queryset.select_for_update()
        return get_object_or_404(queryset, pk=slot_id)


def ensure_can_publish(experience, new_status):
    """公開（public）にする条件。画像が1枚以上必要"""
    if new_status == PublishStatus.PUBLIC and not experience.experience_images.exists():
        raise Conflict("IMAGE_REQUIRED", "公開するには画像を1枚以上登録してください。")


def has_reservations(**filters):
    """予約されたことがあるか（キャンセル済みも含む）"""
    return Reservation.objects.filter(**filters).exists()


# =========================================================
# 体験一覧・登録
# =========================================================

class ExperienceListCreateView(ProducerExperienceView):

    def get(self, request):
        query = validate_query(ExperienceListQuerySerializer, request)
        queryset = Experience.objects.filter(producer=self.producer)
        if "publish_status" in query:
            queryset = queryset.filter(publish_status=query["publish_status"])

        # 枠の数・申込の数・次回開催日時は、JOIN して集計し、一覧と同じ1回の SQL で取る
        annotated = queryset.annotate(
            slot_count=Count("experience_slots", distinct=True),
            application_count=Count("experience_slots__reservations", distinct=True),
            next_start_at=Min("experience_slots__start_at", filter=Q(
                experience_slots__status=ExperienceSlot.Status.OPEN,
                experience_slots__start_at__gt=timezone.now(),
            )),
        ).order_by("-created_at", "-id")
        return Response(paginate(annotated, query, ExperienceSummarySerializer, count_queryset=queryset))

    @transaction.atomic
    def post(self, request):
        producer = self.producer
        ensure_producer_not_suspended(producer)
        serializer = ExperienceWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        experience = Experience(producer=producer, **data)
        if "prefecture" not in data:
            experience.prefecture = producer.prefecture
        # 画像はまだ登録できないので、公開を選ぶと 409 になる
        if experience.publish_status == PublishStatus.PUBLIC:
            raise Conflict("IMAGE_REQUIRED", "公開するには画像を1枚以上登録してください。")
        experience.save()
        return Response(ExperienceWriteResponseSerializer(experience).data, status=status.HTTP_201_CREATED)


# =========================================================
# 体験詳細・更新・削除
# =========================================================

class ExperienceDetailView(ProducerExperienceView):

    def get(self, request, experience_id):
        experience = get_object_or_404(
            Experience.objects.filter(producer=self.producer).prefetch_related("experience_images"),
            pk=experience_id,
        )
        return Response(ExperienceDetailSerializer(experience).data)

    @transaction.atomic
    def patch(self, request, experience_id):
        ensure_producer_not_suspended(self.producer)
        experience = self.get_experience(experience_id, lock=True)
        serializer = ExperienceWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        new_status = data.get("publish_status")
        if new_status is not None and new_status != experience.publish_status:
            if experience.publish_status == PublishStatus.SUSPENDED:
                raise Conflict("CONTENT_SUSPENDED",
                                "運営により掲載停止中のため、公開状態は変更できません。")
            ensure_can_publish(experience, new_status)

        # 料金を変えても、既存の予約の total_amount はそのまま（予約時に保存済み）
        for field, value in data.items():
            setattr(experience, field, value)
        experience.save()
        return Response(ExperienceWriteResponseSerializer(experience).data)

    @transaction.atomic
    def delete(self, request, experience_id):
        ensure_producer_not_suspended(self.producer)
        experience = self.get_experience(experience_id, lock=True)
        if has_reservations(slot__experience=experience):
            raise Conflict("HAS_RESERVATIONS",
                            "予約されたことがある体験は削除できません。非公開にしてください。")
        experience.delete()  # 予約枠・画像も一緒に消える（S3 のファイルは消さない）
        return Response(status=status.HTTP_204_NO_CONTENT)


# =========================================================
# 体験申込者一覧
# =========================================================

class ExperienceApplicationListView(ProducerExperienceView):

    def get(self, request, experience_id):
        experience = self.get_experience(experience_id)
        query = validate_query(ApplicationQuerySerializer, request)

        queryset = Reservation.objects.filter(slot__experience=experience)
        if "slot_id" in query:
            self.get_slot(experience, query["slot_id"])  # 別の体験の枠なら 404
            queryset = queryset.filter(slot_id=query["slot_id"])
        if "status" in query:
            queryset = queryset.filter(status=query["status"])
        queryset = queryset.select_related("slot", "user").order_by("-created_at", "-id")
        return Response(paginate(queryset, query, ApplicationSerializer))


# =========================================================
# 予約枠一覧・登録
# =========================================================

class SlotListCreateView(ProducerExperienceView):

    def get(self, request, experience_id):
        experience = self.get_experience(experience_id)
        query = validate_query(SlotQuerySerializer, request)
        queryset = ExperienceSlot.objects.filter(experience=experience)
        if "status" in query:
            queryset = queryset.filter(status=query["status"])
        return Response(paginate(queryset.order_by("start_at", "id"), query, SlotSerializer))

    @transaction.atomic
    def post(self, request, experience_id):
        ensure_producer_not_suspended(self.producer)
        experience = self.get_experience(experience_id, lock=True)  # 同じ日時の枠の二重登録を防ぐ
        serializer = SlotCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        ensure_no_duplicate_slot(experience, data["start_at"])
        slot = ExperienceSlot.objects.create(experience=experience, reserved_count=0, **data)
        return Response(SlotSerializer(slot).data, status=status.HTTP_201_CREATED)


def ensure_no_duplicate_slot(experience, start_at, exclude_id=None):
    queryset = ExperienceSlot.objects.filter(experience=experience, start_at=start_at)
    if exclude_id is not None:
        queryset = queryset.exclude(pk=exclude_id)
    if queryset.exists():
        raise Conflict("DUPLICATE_SLOT", "同じ開催日時の予約枠がすでにあります。")


# =========================================================
# 予約枠更新・中止・削除
# =========================================================

class SlotDetailView(ProducerExperienceView):

    @transaction.atomic
    def patch(self, request, experience_id, slot_id):
        serializer = SlotUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        canceling = data.get("status") == ExperienceSlot.Status.CANCELED
        if not canceling:
            ensure_producer_not_suspended(self.producer)  # 中止だけは掲載停止中でもできる

        experience = self.get_experience(experience_id, lock=True)
        slot = self.get_slot(experience, slot_id, lock=True)
        ensure_slot_editable(slot)

        if canceling:
            cancel_slot(experience, slot)
            return Response(SlotSerializer(slot).data)

        changing_time = any(
            field in data and data[field] != getattr(slot, field) for field in ("start_at", "duration_min"))
        if changing_time and has_reservations(slot=slot):
            raise Conflict("SLOT_TIME_LOCKED", "予約がある予約枠は、開催日時・所要時間を変更できません。")
        if "capacity" in data and data["capacity"] < slot.reserved_count:
            raise Conflict("CAPACITY_BELOW_RESERVED", "定員は現在の予約人数より少なくできません。")
        if "start_at" in data:
            ensure_no_duplicate_slot(experience, data["start_at"], exclude_id=slot.pk)

        for field, value in data.items():
            setattr(slot, field, value)
        slot.save()
        return Response(SlotSerializer(slot).data)

    @transaction.atomic
    def delete(self, request, experience_id, slot_id):
        ensure_producer_not_suspended(self.producer)
        experience = self.get_experience(experience_id, lock=True)
        slot = self.get_slot(experience, slot_id, lock=True)
        if slot.start_at <= timezone.now():
            raise Conflict("SLOT_NOT_EDITABLE", "開始済みの予約枠は削除できません。")
        if has_reservations(slot=slot):
            raise Conflict("HAS_RESERVATIONS",
                           "予約されたことがある予約枠は削除できません。中止にしてください。")
        slot.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


def ensure_slot_editable(slot):
    if slot.status == ExperienceSlot.Status.CANCELED:
        raise Conflict("SLOT_NOT_EDITABLE", "中止済みの予約枠は変更できません。")
    if slot.start_at <= timezone.now():
        raise Conflict("SLOT_NOT_EDITABLE", "開始済みの予約枠は変更できません。")


def cancel_slot(experience, slot):
    """予約枠を中止する。申込済み・確定済みの予約をすべてキャンセルし、予約者に通知とメールを送る

    体験の支払いは当日現地なので返金はない。呼び出し側で体験・予約枠をロックしておく。
    """
    reservations = list(
        Reservation.objects.select_for_update().select_related("user")
        .filter(slot=slot, status__in=ACTIVE_RESERVATION_STATUSES).order_by("id")
    )
    released = sum(r.adult_count + r.child_count + r.infant_count for r in reservations)
    Reservation.objects.filter(pk__in=[r.pk for r in reservations]).update(
        status=Reservation.Status.CANCELED, updated_at=timezone.now())

    slot.status = ExperienceSlot.Status.CANCELED
    slot.reserved_count = max(slot.reserved_count - released, 0)
    slot.save(update_fields=["status", "reserved_count", "updated_at"])

    start = timezone.localtime(slot.start_at).strftime("%Y年%m月%d日 %H:%M")
    for reservation in reservations:
        notify(
            reservation.user,
            Notification.NotificationType.RESERVATION,
            title="体験の開催が中止になりました",
            body=(
                f"ご予約の体験「{experience.title}」（{start}〜）は、主催者の都合により中止になりました。\n"
                f"予約番号 {reservation.reservation_no} の予約はキャンセルされました。\n"
                "参加費は当日現地でのお支払いのため、返金の手続きはありません。\n"
            ),
        )
