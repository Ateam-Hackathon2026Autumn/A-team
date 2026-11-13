"""体験（公開側・申込） のシリアライザー

使う view: api/views/public/experiences.py

実装済み:
  - ExperienceListQuerySerializer: 一覧のクエリ（page・pageSize・areaId・prefectureId・producerId）
  - ExperienceSummarySerializer: 一覧の1件
      {id, title, prefectureId, prefectureName, areaId, priceAdult, priceChild, familyOk, beginnerOk, thumbnailUrl,
       producer, nextStartAt}
      thumbnail_key（サブクエリ）・upcoming_slots（これからの受付中の日程、Prefetch の to_attr）を view で付けておく
  - ExperienceDetailQuerySerializer: 詳細のクエリ（slotsPage・slotsPageSize）
  - ExperienceDetailSerializer: 詳細。一覧の項目＋description・images・place・ageCondition・flow（[{time, text}]）・
      belongings・notes・cancelPolicy。slots は view が足す
  - SlotSerializer: 日程1件 {id, startAt, durationMin, capacity, remainingCapacity, bookingDeadlineAt, bookable}
  - ApplicationCreateSerializer: 申込の本文
  - ReservationSerializer: 申込（201）のレスポンス
  - MyApplicationQuerySerializer / MyApplicationSerializer: 申込状況（GET /users/me/experience-applications）
      1件 {id, reservationNo, experience: {id, title, isPublic}, slot: {id, startAt, durationMin, status},
           adultCount, childCount, infantCount, totalAmount, status, cancellable, cancelDeadlineAt, createdAt}
      context["public_experience_ids"]（公開中の体験の ID の集合）を view で渡す

入力エラーは 400（項目ごとのメッセージ）。カラム名は claude/er-diagram.md に合わせる
"""
from rest_framework import serializers

from marche.models import Experience, ExperienceImage, ExperienceSlot, Reservation

from ...common.images import ImageUrlField
from ...common.pagination import PageQuerySerializer
from ...common.serializers import QuerySerializer, StrictSerializer
from ...services.reservations import booking_deadline, is_bookable, is_cancellable
from .catalog import ProducerSummarySerializer
from .orders import check_name_length, normalize_phone

MAX_ID = 2 ** 63 - 1
MAX_PEOPLE = 99
MAX_AMOUNT = 2_147_483_647


class ExperienceListQuerySerializer(PageQuerySerializer):
    area_id = serializers.IntegerField(required=False, min_value=1, max_value=MAX_ID)
    prefecture_id = serializers.IntegerField(required=False, min_value=1, max_value=MAX_ID)
    producer_id = serializers.IntegerField(required=False, min_value=1, max_value=MAX_ID)


class ExperienceSummarySerializer(serializers.ModelSerializer):
    prefecture_name = serializers.CharField(source="prefecture.name")
    area_id = serializers.IntegerField(source="prefecture.area_id")
    thumbnail_url = ImageUrlField(source="thumbnail_key")
    producer = ProducerSummarySerializer()
    next_start_at = serializers.SerializerMethodField()

    class Meta:
        model = Experience
        fields = ["id", "title", "prefecture_id", "prefecture_name", "area_id", "price_adult", "price_child",
                  "family_ok", "beginner_ok", "thumbnail_url", "producer", "next_start_at"]

    def get_next_start_at(self, experience):
        """受付中で締め切り前の一番早い日程（満席も含む）。upcoming_slots は開始日時の順"""
        for slot in experience.upcoming_slots:
            if booking_deadline(slot, experience) > self.context["now"]:
                return serializers.DateTimeField().to_representation(slot.start_at)
        return None


class ExperienceImageSerializer(serializers.ModelSerializer):
    url = ImageUrlField(source="image")

    class Meta:
        model = ExperienceImage
        fields = ["id", "url", "sort_order"]


class ExperienceDetailQuerySerializer(QuerySerializer):
    slots_page = serializers.IntegerField(required=False, default=1, min_value=1, max_value=1_000_000)
    slots_page_size = serializers.IntegerField(required=False, default=20, min_value=1, max_value=100)


class ExperienceDetailSerializer(ExperienceSummarySerializer):
    images = ExperienceImageSerializer(source="experience_images", many=True)

    class Meta(ExperienceSummarySerializer.Meta):
        fields = ExperienceSummarySerializer.Meta.fields + [
            "description", "images", "place", "age_condition", "flow", "belongings", "notes", "cancel_policy"]


class SlotSerializer(serializers.ModelSerializer):
    """日程。context["experience"]・context["now"] を渡す"""

    remaining_capacity = serializers.SerializerMethodField()
    booking_deadline_at = serializers.SerializerMethodField()
    bookable = serializers.SerializerMethodField()

    class Meta:
        model = ExperienceSlot
        fields = ["id", "start_at", "duration_min", "capacity", "remaining_capacity", "booking_deadline_at",
                  "bookable"]

    def get_remaining_capacity(self, slot):
        return max(slot.capacity - slot.reserved_count, 0)

    def get_booking_deadline_at(self, slot):
        return serializers.DateTimeField().to_representation(booking_deadline(slot, self.context["experience"]))

    def get_bookable(self, slot):
        return is_bookable(slot, self.context["experience"], self.context["now"])


class ApplicationCreateSerializer(StrictSerializer):
    """POST /experiences/:experienceId/applications の本文"""

    slot_id = serializers.IntegerField(min_value=1, max_value=MAX_ID)
    adult_count = serializers.IntegerField(min_value=1, max_value=MAX_PEOPLE)
    child_count = serializers.IntegerField(min_value=0, max_value=MAX_PEOPLE)
    infant_count = serializers.IntegerField(min_value=0, max_value=MAX_PEOPLE)
    last_name = serializers.CharField(max_length=50)
    first_name = serializers.CharField(max_length=50)
    phone = serializers.CharField(max_length=20)
    message = serializers.CharField(max_length=2000, required=False, allow_null=True, allow_blank=True)
    agreed_to_cancel_policy = serializers.BooleanField()
    eligibility_confirmed = serializers.BooleanField()
    expected_total_amount = serializers.IntegerField(min_value=0, max_value=MAX_AMOUNT)

    def validate_phone(self, value):
        return normalize_phone(value)

    def validate_message(self, value):
        return value or None

    def validate_agreed_to_cancel_policy(self, value):
        if value is not True:
            raise serializers.ValidationError("キャンセルポリシーへの同意が必要です。")
        return value

    def validate_eligibility_confirmed(self, value):
        if value is not True:
            raise serializers.ValidationError("参加条件の確認が必要です。")
        return value

    def validate(self, data):
        if data["adult_count"] + data["child_count"] + data["infant_count"] > MAX_PEOPLE:
            raise serializers.ValidationError({"adult_count": [f"人数は合わせて{MAX_PEOPLE}人までです。"]})
        check_name_length(data)
        return data


class ReservationSerializer(serializers.ModelSerializer):
    experience_id = serializers.IntegerField(source="slot.experience_id")

    class Meta:
        model = Reservation
        fields = ["id", "reservation_no", "experience_id", "slot_id", "adult_count", "child_count", "infant_count",
                  "representative_name", "phone", "message", "total_amount", "status", "policy_agreed_at",
                  "created_at"]


class MyApplicationQuerySerializer(PageQuerySerializer):
    status = serializers.ChoiceField(choices=Reservation.Status.choices, required=False)


class MyApplicationSerializer(serializers.ModelSerializer):
    """申込状況の1件。slot__experience を select_related しておく。context に now・public_experience_ids"""

    experience = serializers.SerializerMethodField()
    slot = serializers.SerializerMethodField()
    cancellable = serializers.SerializerMethodField()
    cancel_deadline_at = serializers.SerializerMethodField()

    class Meta:
        model = Reservation
        fields = ["id", "reservation_no", "experience", "slot", "adult_count", "child_count", "infant_count",
                  "total_amount", "status", "cancellable", "cancel_deadline_at", "created_at"]

    def get_experience(self, reservation):
        experience = reservation.slot.experience
        is_public = experience.id in self.context["public_experience_ids"]
        return {"id": experience.id, "title": experience.title if is_public else None, "is_public": is_public}

    def get_slot(self, reservation):
        slot = reservation.slot
        return {"id": slot.id, "start_at": serializers.DateTimeField().to_representation(slot.start_at),
                "duration_min": slot.duration_min, "status": slot.status}

    def get_cancellable(self, reservation):
        return is_cancellable(reservation, self.context["now"])

    def get_cancel_deadline_at(self, reservation):
        return serializers.DateTimeField().to_representation(
            booking_deadline(reservation.slot, reservation.slot.experience))
