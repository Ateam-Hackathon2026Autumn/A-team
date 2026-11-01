"""
生産者ダッシュボード：体験管理API

GET    /api/v1/dashboard/experiences/
POST   /api/v1/dashboard/experiences/

GET    /api/v1/dashboard/experiences/<experience_id>/
PATCH  /api/v1/dashboard/experiences/<experience_id>/
DELETE /api/v1/dashboard/experiences/<experience_id>/

GET    /api/v1/dashboard/experiences/<experience_id>/applications/

GET    /api/v1/dashboard/experiences/<experience_id>/slots/
POST   /api/v1/dashboard/experiences/<experience_id>/slots/

PATCH  /api/v1/dashboard/experiences/<experience_id>/slots/<slot_id>/
DELETE /api/v1/dashboard/experiences/<experience_id>/slots/<slot_id>/
"""

from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models import (
    Experience,
    ExperienceSlot,
    Prefecture,
    Reservation,
)

from api.serializers.dashboard.experiences import (
    DashboardExperienceIdSerializer,
    DashboardExperienceSlotIdSerializer,
    DashboardExperienceListQuerySerializer,
    DashboardExperienceResponseSerializer,
    DashboardExperienceListResponseSerializer,
    DashboardExperienceCreateSerializer,
    DashboardExperienceUpdateSerializer,
    DashboardExperienceDeleteResponseSerializer,
    DashboardExperienceApplicationQuerySerializer,
    DashboardExperienceApplicationListResponseSerializer,
    DashboardExperienceSlotQuerySerializer,
    DashboardExperienceSlotListResponseSerializer,
    DashboardExperienceSlotCreateSerializer,
    DashboardExperienceSlotUpdateSerializer,
    DashboardExperienceSlotDeleteResponseSerializer,
)


class DashboardExperienceBaseView(APIView):
    """
    体験管理APIの共通処理。

    現時点ではログイン中の生産者を request.user.producer から取得する。
    共通権限処理が完成したら、そのインターフェースに合わせて統合する。
    """

    permission_classes = [IsAuthenticated]

    def get_experience(self, request, experience_id):
        """
        ログイン中の生産者自身の体験だけを取得する。
        """

        producer = request.user.producer

        return get_object_or_404(
            Experience.objects.prefetch_related(
                "experience_images",
                "experience_slots",
            ),
            pk=experience_id,
            producer=producer,
        )


# =========================================================
# 体験一覧・新規登録
# =========================================================

class ExperienceListCreateView(DashboardExperienceBaseView):
    """
    体験一覧取得・新規登録
    """

    def get(self, request):
        """
        GET /api/v1/dashboard/experiences/

        ログイン中の生産者が登録した体験一覧を返す。
        """

        producer = request.user.producer

        query_serializer = DashboardExperienceListQuerySerializer(
            data=request.query_params
        )
        query_serializer.is_valid(raise_exception=True)

        query = query_serializer.validated_data

        experiences = Experience.objects.filter(
            producer=producer
        ).prefetch_related(
            "experience_images",
            "experience_slots",
        ).order_by("-created_at")

        # 公開状態による絞り込み
        publish_status = query.get("publish_status")

        if publish_status:
            experiences = experiences.filter(
                publish_status=publish_status
            )

        # キーワード検索
        search = query.get("search")

        if search:
            experiences = experiences.filter(
                Q(title__icontains=search)
                | Q(description__icontains=search)
                | Q(place__icontains=search)
            )

        # ページネーション
        page = query.get("page", 1)
        page_size = query.get("page_size", 20)

        total = experiences.count()

        start = (page - 1) * page_size
        end = start + page_size

        experiences = experiences[start:end]

        response_serializer = DashboardExperienceListResponseSerializer(
            {
                "total": total,
                "page": page,
                "page_size": page_size,
                "results": experiences,
            }
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_200_OK,
        )

    @transaction.atomic
    def post(self, request):
        """
        POST /api/v1/dashboard/experiences/

        体験を新規登録する。
        """

        producer = request.user.producer

        serializer = DashboardExperienceCreateSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        validated_data = serializer.validated_data.copy()

        # 都道府県
        prefecture_id = validated_data.pop(
            "prefecture_id",
            None,
        )

        if prefecture_id is not None:
            prefecture = get_object_or_404(
                Prefecture,
                pk=prefecture_id,
            )
        else:
            prefecture = producer.prefecture

        # 画像登録機能が未実装のため、公開状態での登録は制限する。
        # TODO: ExperienceImage登録API完成後に画像の有無を確認する。
        publish_status = validated_data.get(
            "publish_status",
            "draft",
        )

        if publish_status == "public":
            return Response(
                {
                    "detail": (
                        "画像登録機能が完成するまで体験を公開できません。"
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        experience = Experience.objects.create(
            producer=producer,
            prefecture=prefecture,
            **validated_data,
        )

        response_serializer = DashboardExperienceResponseSerializer(
            experience
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
        )


# =========================================================
# 体験詳細・更新・削除
# =========================================================

class ExperienceDetailView(DashboardExperienceBaseView):
    """
    体験詳細取得・更新・削除
    """

    def get(self, request, experience_id):
        """
        GET /api/v1/dashboard/experiences/<experience_id>/
        """

        experience = self.get_experience(
            request,
            experience_id,
        )

        serializer = DashboardExperienceResponseSerializer(
            experience
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    @transaction.atomic
    def patch(self, request, experience_id):
        """
        PATCH /api/v1/dashboard/experiences/<experience_id>/

        体験情報を更新する。

        料金を変更しても既存予約の total_amount は変更しない。
        """

        experience = self.get_experience(
            request,
            experience_id,
        )

        serializer = DashboardExperienceUpdateSerializer(
            experience,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)

        validated_data = serializer.validated_data.copy()

        # 都道府県の変更
        prefecture_id = validated_data.pop(
            "prefecture_id",
            None,
        )

        if prefecture_id is not None:
            validated_data["prefecture"] = get_object_or_404(
                Prefecture,
                pk=prefecture_id,
            )

        # 既存予約の total_amount は変更しない。
        for field, value in validated_data.items():
            setattr(experience, field, value)

        experience.save()

        response_serializer = DashboardExperienceResponseSerializer(
            experience
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_200_OK,
        )

    @transaction.atomic
    def delete(self, request, experience_id):
        """
        DELETE /api/v1/dashboard/experiences/<experience_id>/

        予約履歴がある体験は削除できない。
        """

        experience = self.get_experience(
            request,
            experience_id,
        )

        # 予約履歴の有無を確認
        has_reservation = Reservation.objects.filter(
            slot__experience=experience,
        ).exists()

        if has_reservation:
            return Response(
                {
                    "detail": (
                        "予約履歴がある体験は削除できません。"
                        "公開状態を非公開に変更してください。"
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        experience.delete()

        response_serializer = DashboardExperienceDeleteResponseSerializer(
            {
                "message": "体験を削除しました。"
            }
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_200_OK,
        )


# =========================================================
# 体験申込者一覧
# =========================================================

class ExperienceApplicationListView(DashboardExperienceBaseView):
    """
    体験申込者一覧
    """

    def get(self, request, experience_id):
        """
        GET /api/v1/dashboard/experiences/<experience_id>/applications/

        体験に紐づく予約情報を取得する。
        """

        experience = self.get_experience(
            request,
            experience_id,
        )

        query_serializer = DashboardExperienceApplicationQuerySerializer(
            data=request.query_params
        )
        query_serializer.is_valid(raise_exception=True)

        query = query_serializer.validated_data

        reservations = Reservation.objects.filter(
            slot__experience=experience,
        ).select_related(
            "slot",
            "user",
        ).order_by("-created_at")

        # 予約枠による絞り込み
        slot_id = query.get("slot_id")

        if slot_id:
            reservations = reservations.filter(
                slot_id=slot_id,
            )

        # 予約ステータスによる絞り込み
        reservation_status = query.get("status")

        if reservation_status:
            reservations = reservations.filter(
                status=reservation_status,
            )

        # ページネーション
        page = query.get("page", 1)
        page_size = query.get("page_size", 20)

        total = reservations.count()

        start = (page - 1) * page_size
        end = start + page_size

        reservations = reservations[start:end]

        response_serializer = (
            DashboardExperienceApplicationListResponseSerializer(
                {
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "results": reservations,
                }
            )
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_200_OK,
        )


# =========================================================
# 予約枠一覧・新規登録
# =========================================================

class ExperienceSlotListCreateView(DashboardExperienceBaseView):
    """
    予約枠一覧取得・新規登録
    """

    def get(self, request, experience_id):
        """
        GET /api/v1/dashboard/experiences/<experience_id>/slots/
        """

        experience = self.get_experience(
            request,
            experience_id,
        )

        query_serializer = DashboardExperienceSlotQuerySerializer(
            data=request.query_params
        )
        query_serializer.is_valid(raise_exception=True)

        query = query_serializer.validated_data

        slots = ExperienceSlot.objects.filter(
            experience=experience,
        ).order_by("start_at")

        slot_status = query.get("status")

        if slot_status:
            slots = slots.filter(
                status=slot_status,
            )

        page = query.get("page", 1)
        page_size = query.get("page_size", 20)

        total = slots.count()

        start = (page - 1) * page_size
        end = start + page_size

        slots = slots[start:end]

        response_serializer = (
            DashboardExperienceSlotListResponseSerializer(
                {
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "results": slots,
                }
            )
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_200_OK,
        )

    @transaction.atomic
    def post(self, request, experience_id):
        """
        POST /api/v1/dashboard/experiences/<experience_id>/slots/

        予約枠を1件登録する。
        start_at は未来の日時である必要がある。
        """

        experience = self.get_experience(
            request,
            experience_id,
        )

        serializer = DashboardExperienceSlotCreateSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        slot = serializer.save(
            experience=experience,
            reserved_count=0,
        )

        response_serializer = (
            DashboardExperienceSlotListResponseSerializer
        )

        # 1件登録のため、単体レスポンスを返す。
        from api.serializers.dashboard.experiences import (
            DashboardExperienceSlotResponseSerializer,
        )

        return Response(
            DashboardExperienceSlotResponseSerializer(slot).data,
            status=status.HTTP_201_CREATED,
        )


# =========================================================
# 予約枠更新・中止・削除
# =========================================================

class ExperienceSlotDetailView(DashboardExperienceBaseView):
    """
    予約枠更新・中止・削除
    """

    def get_slot(self, request, experience_id, slot_id):
        """
        ログイン中の生産者自身の体験に属する予約枠だけを取得する。
        """

        experience = self.get_experience(
            request,
            experience_id,
        )

        return get_object_or_404(
            ExperienceSlot,
            pk=slot_id,
            experience=experience,
        )

    @transaction.atomic
    def patch(self, request, experience_id, slot_id):
        """
        PATCH /api/v1/dashboard/experiences/<experience_id>/slots/<slot_id>/

        予約枠を更新する。

        ・過去または中止済みの予約枠は更新不可
        ・予約がある場合、start_at / duration_min は変更不可
        ・capacity は reserved_count 以上
        ・中止処理は関連する通知・メール・返金処理が完成するまで実行不可
        """

        slot = self.get_slot(
            request,
            experience_id,
            slot_id,
        )

        if slot.start_at <= timezone.now():
            return Response(
                {
                    "detail": "過去または開始済みの予約枠は更新できません。"
                },
                status=status.HTTP_409_CONFLICT,
            )

        if slot.status == "canceled":
            return Response(
                {
                    "detail": "中止済みの予約枠は更新できません。"
                },
                status=status.HTTP_409_CONFLICT,
            )

        serializer = DashboardExperienceSlotUpdateSerializer(
            slot,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)

        validated_data = serializer.validated_data

        # 中止処理は関連機能が未完成のため一時停止する。
        if validated_data.get("status") == "canceled":
            # TODO:
            # ・確定済み予約のキャンセル
            # ・reserved_count の整合性確認
            # ・予約者への通知
            # ・予約者へのメール送信
            # ・決済返金の仕様確認と実装
            return Response(
                {
                    "detail": (
                        "予約枠の中止機能は現在準備中です。"
                    )
                },
                status=status.HTTP_501_NOT_IMPLEMENTED,
            )

        # 予約履歴の有無
        has_reservation = Reservation.objects.filter(
            slot=slot,
        ).exists()

        # 予約がある場合、日時と所要時間は変更不可
        if has_reservation:
            if (
                "start_at" in validated_data
                or "duration_min" in validated_data
            ):
                return Response(
                    {
                        "detail": (
                            "予約がある予約枠の開始日時・所要時間は変更できません。"
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )

        # 定員は予約済み人数を下回れない
        new_capacity = validated_data.get(
            "capacity",
            slot.capacity,
        )

        if new_capacity < slot.reserved_count:
            return Response(
                {
                    "detail": (
                        "定員は現在の予約数を下回る値に変更できません。"
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        for field, value in validated_data.items():
            setattr(slot, field, value)

        slot.save()

        from api.serializers.dashboard.experiences import (
            DashboardExperienceSlotResponseSerializer,
        )

        return Response(
            DashboardExperienceSlotResponseSerializer(slot).data,
            status=status.HTTP_200_OK,
        )

    @transaction.atomic
    def delete(self, request, experience_id, slot_id):
        """
        DELETE /api/v1/dashboard/experiences/<experience_id>/slots/<slot_id>/

        予約履歴がある予約枠は削除できない。
        過去の予約枠も削除できない。
        """

        slot = self.get_slot(
            request,
            experience_id,
            slot_id,
        )

        if slot.start_at <= timezone.now():
            return Response(
                {
                    "detail": "過去または開始済みの予約枠は削除できません。"
                },
                status=status.HTTP_409_CONFLICT,
            )

        has_reservation = Reservation.objects.filter(
            slot=slot,
        ).exists()

        if has_reservation:
            return Response(
                {
                    "detail": (
                        "予約履歴がある予約枠は削除できません。"
                        "中止処理を行ってください。"
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        slot.delete()

        from api.serializers.dashboard.experiences import (
            DashboardExperienceSlotDeleteResponseSerializer,
        )

        response_serializer = (
            DashboardExperienceSlotDeleteResponseSerializer(
                {
                    "message": "予約枠を削除しました。"
                }
            )
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_200_OK,
        )