"""体験（公開側・申込）

認証: 一覧・詳細は公開。申込・申込状況・キャンセルは会員（未ログインは 401）。メール未確認でも使える
仕様: Notion の各API定義＋api-spec.md「7. 実装で決めたこと」ステップ8。カラム名: claude/er-diagram.md
公開条件: 体験が public かつ生産者が公開中（services/visibility.py の public_content）

実装済み:
  - 体験一覧: GET /api/v1/experiences
      ・areaId（開催地の都道府県のエリア）・prefectureId・producerId で絞り込み（AND）。存在しない ID は200の空配列
      ・created_at・id の降順。満席・開催予定のない体験も出す。ページングは共通の形
      ・nextStartAt は受付中で締め切り前の一番早い日程の開始日時（満席も含む。なければ null）
  - 体験詳細: GET /api/v1/experiences/:experienceId
      ・一覧の項目＋description・images・place・ageCondition・flow・belongings・notes・cancelPolicy・slots
      ・slots はこれから開催される受付中の日程（満席も含む）を start_at・id の順。slotsPage・slotsPageSize でページング
        1件に remainingCapacity・bookingDeadlineAt（締め切り日時）・bookable（今申し込めるか）
      ・公開対象外・存在しない体験は 404 EXPERIENCE_NOT_FOUND
  - 申込: POST /api/v1/experiences/:experienceId/applications
      ・services/reservations.py の apply_for_experience。201 で予約
  - 申込状況: GET /api/v1/users/me/experience-applications
      ・自分の予約を created_at・id の降順。status で絞り込み。体験が非公開になったら title は null・isPublic=false
      ・1件に cancellable（キャンセルできるか）・cancelDeadlineAt（締め切り日時）
  - キャンセル: POST /api/v1/users/me/experience-applications/:applicationId/cancel
      ・本文なし。確定済み・締め切り前だけ（それ以外は 409 CANCEL_NOT_ALLOWED）。200 で申込状況の1件
      ・他人・存在しない予約は 404 RESERVATION_NOT_FOUND
"""
from django.db.models import OuterRef, Prefetch, Subquery
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from marche.models import Experience, ExperienceImage, ExperienceSlot, Reservation

from ...common.exceptions import ApiError
from ...common.pagination import paginate, validate_query
from ...common.serializers import StrictSerializer
from ...serializers.public.experiences import (
    MAX_ID,
    ApplicationCreateSerializer,
    ExperienceDetailQuerySerializer,
    ExperienceDetailSerializer,
    ExperienceListQuerySerializer,
    ExperienceSummarySerializer,
    MyApplicationQuerySerializer,
    MyApplicationSerializer,
    ReservationSerializer,
    SlotSerializer,
)
from ...services.reservations import apply_for_experience, cancel_reservation, experience_not_found
from ...services.visibility import public_content


def upcoming_slots(now):
    return ExperienceSlot.objects.filter(status=ExperienceSlot.Status.OPEN, start_at__gt=now).order_by("start_at", "id")


def public_experiences(now):
    thumbnail = ExperienceImage.objects.filter(experience=OuterRef("pk")).order_by("sort_order", "id").values("image")[:1]
    return (public_content(Experience.objects.all())
            .select_related("prefecture", "producer__prefecture")
            .annotate(thumbnail_key=Subquery(thumbnail))
            .prefetch_related(Prefetch("experience_slots", queryset=upcoming_slots(now), to_attr="upcoming_slots")))


class ExperienceListView(APIView):
    """GET /api/v1/experiences"""

    permission_classes = [AllowAny]

    def get(self, request):
        query = validate_query(ExperienceListQuerySerializer, request)
        now = timezone.now()
        filters = {}
        if "area_id" in query:
            filters["prefecture__area_id"] = query["area_id"]
        if "prefecture_id" in query:
            filters["prefecture_id"] = query["prefecture_id"]
        if "producer_id" in query:
            filters["producer_id"] = query["producer_id"]
        experiences = public_experiences(now).filter(**filters).order_by("-created_at", "-id")
        count = public_content(Experience.objects.all()).filter(**filters)
        return Response(paginate(experiences, query, ExperienceSummarySerializer, count_queryset=count,
                                 context={"now": now}))


class ExperienceDetailView(APIView):
    """GET /api/v1/experiences/:experienceId"""

    permission_classes = [AllowAny]

    def get(self, request, experience_id):
        query = validate_query(ExperienceDetailQuerySerializer, request)
        now = timezone.now()
        experience = None
        if experience_id <= MAX_ID:
            experience = (public_experiences(now).prefetch_related("experience_images")
                          .filter(pk=experience_id).first())
        if experience is None:
            raise experience_not_found()
        context = {"now": now, "experience": experience}
        body = ExperienceDetailSerializer(experience, context=context).data
        slot_query = {"page": query["slots_page"], "page_size": query["slots_page_size"]}
        body["slots"] = paginate(upcoming_slots(now).filter(experience=experience), slot_query, SlotSerializer,
                                 context=context)
        return Response(body)


class ExperienceApplicationCreateView(APIView):
    """POST /api/v1/experiences/:experienceId/applications"""

    permission_classes = [IsAuthenticated]

    def post(self, request, experience_id):
        serializer = ApplicationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if experience_id > MAX_ID:
            raise experience_not_found()
        reservation = apply_for_experience(experience_id, request.user, serializer.validated_data)
        reservation = Reservation.objects.select_related("slot").get(pk=reservation.pk)
        return Response(ReservationSerializer(reservation).data, status=status.HTTP_201_CREATED)


def my_application_context(user, now):
    public_ids = set(public_content(Experience.objects.filter(experience_slots__reservations__user=user))
                     .values_list("id", flat=True))
    return {"now": now, "public_experience_ids": public_ids}


class MyExperienceApplicationListView(APIView):
    """GET /api/v1/users/me/experience-applications"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = validate_query(MyApplicationQuerySerializer, request)
        reservations = Reservation.objects.filter(user=request.user)
        if "status" in query:
            reservations = reservations.filter(status=query["status"])
        items = reservations.select_related("slot__experience").order_by("-created_at", "-id")
        return Response(paginate(items, query, MyApplicationSerializer, count_queryset=reservations,
                                 context=my_application_context(request.user, timezone.now())))


class MyExperienceApplicationCancelView(APIView):
    """POST /api/v1/users/me/experience-applications/:applicationId/cancel"""

    permission_classes = [IsAuthenticated]

    def post(self, request, application_id):
        StrictSerializer(data=request.data or {}).is_valid(raise_exception=True)  # 本文は受け付けない
        if application_id > MAX_ID:
            raise ApiError(status.HTTP_404_NOT_FOUND, "RESERVATION_NOT_FOUND", "予約が見つかりません。")
        cancel_reservation(application_id, request.user)
        reservation = Reservation.objects.select_related("slot__experience").get(pk=application_id)
        context = my_application_context(request.user, timezone.now())
        return Response(MyApplicationSerializer(reservation, context=context).data)
