"""生産者申請

認証: 会員（ログイン必須。メール未確認でも申請できる）
仕様: Notion の各API定義＋api-spec.md「7. 実装で決めたこと」。カラム名: claude/er-diagram.md
申請書類は今回は扱わない（拡張。application_documents は使わない）。

このファイルの API（シーケンス図は Notion の「生産者申請状況・修正」）:
    - 生産者登録申請: POST /api/v1/producer-applications
        ・producers（approval_status=pending・publish_status=draft）と producer_applications（pending）を同時に作る
        ・すでに生産者がいれば 409（審査中 APPLICATION_ALREADY_PENDING / 承認済み PRODUCER_ALREADY_APPROVED
          / 差し戻し・却下 APPLICATION_RESUBMIT_REQUIRED（PATCH で再申請する））
        ・201。isProducer は false（承認されるまで生産者の権限はない）
    - 申請状況: GET /api/v1/producer-applications/me
        ・最新の申請（submitted_at・id の降順で先頭）と、今の生産者情報（修正画面の初期値）
        ・申請がなければ 404 APPLICATION_NOT_FOUND
    - 再申請: PATCH /api/v1/producer-applications/me
        ・{applicationId, changes}。applicationId が自分の申請でなければ 404、最新でなければ 409 APPLICATION_CONFLICT
        ・最新の申請が差し戻し・却下でなければ 409 APPLICATION_NOT_RETURNED。生産者が掲載停止中なら 409 PRODUCER_SUSPENDED
        ・changes の項目だけ生産者情報に反映し、approval_status を pending に戻して新しい申請の行を追加する
          （元の審査の履歴は残す。applicationReason を送らなければ前回の申請理由を引き継ぐ）

同時申請: ユーザーの行をロックしてから確かめる（同じ人が2つ作れない。producers.user_id の UNIQUE も効く）。
"""
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from marche.models import Producer, ProducerApplication, PublishStatus, User

from ...common.exceptions import ApiError, Conflict
from ...common.pagination import validate_query
from ...common.permissions import ensure_producer_not_suspended
from ...common.serializers import QuerySerializer
from ...serializers.public.producer_applications import (
    PRODUCER_FIELDS,
    RESUBMITTABLE,
    ApplicationAcceptedSerializer,
    MyApplicationSerializer,
    ProducerApplicationFieldsSerializer,
    ResubmitSerializer,
)
from ...services.storage import validate_image_keys

Status = ProducerApplication.Status


def application_not_found():
    return ApiError(status.HTTP_404_NOT_FOUND, "APPLICATION_NOT_FOUND", "生産者登録申請はありません。")


def validate_images(user, data):
    for field in ("profile_image", "cover_image"):
        if data.get(field):
            validate_image_keys(user, [data[field]], field=field)


def apply_fields(producer, data):
    for field in PRODUCER_FIELDS:
        if field in data:
            setattr(producer, field, data[field])


def latest_application(producer, lock=False):
    queryset = ProducerApplication.objects.filter(producer=producer)
    if lock:
        queryset = queryset.select_for_update()
    return queryset.order_by("-submitted_at", "-id").first()


def accepted(message, producer, application, status_code=status.HTTP_200_OK):
    data = ApplicationAcceptedSerializer({"message": message, "producer": producer, "application": application}).data
    return Response(data, status=status_code)


class ProducerApplicationCreateView(APIView):
    """POST /api/v1/producer-applications"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ProducerApplicationFieldsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        validate_images(request.user, data)

        with transaction.atomic():
            user = User.objects.select_for_update().get(pk=request.user.pk)  # 同じ人の同時申請を1つにする
            existing = Producer.objects.filter(user=user).first()
            if existing is not None:
                raise already_applied(existing)
            producer = Producer(user=user, approval_status=Producer.ApprovalStatus.PENDING,
                                publish_status=PublishStatus.DRAFT)
            apply_fields(producer, data)
            producer.save()
            application = ProducerApplication.objects.create(
                producer=producer, status=Status.PENDING, application_reason=data.get("application_reason") or "",
                submitted_at=timezone.now())
        return accepted("生産者登録申請を受け付けました。", producer, application, status.HTTP_201_CREATED)


def already_applied(producer):
    if producer.approval_status == Producer.ApprovalStatus.PENDING:
        return Conflict("APPLICATION_ALREADY_PENDING", "生産者登録申請は審査中です。")
    if producer.approval_status == Producer.ApprovalStatus.APPROVED:
        return Conflict("PRODUCER_ALREADY_APPROVED", "生産者として登録済みです。")
    return Conflict("APPLICATION_RESUBMIT_REQUIRED", "申請内容を修正して再申請してください。")


class MyProducerApplicationView(APIView):
    """GET・PATCH /api/v1/producer-applications/me"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        validate_query(QuerySerializer, request)  # クエリパラメーターは受け付けない
        producer = Producer.objects.filter(user=request.user).first()
        application = latest_application(producer) if producer else None
        if application is None:
            raise application_not_found()
        return Response(MyApplicationSerializer(application).data)

    def patch(self, request):
        body = ResubmitSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        changes_serializer = ProducerApplicationFieldsSerializer(data=body.validated_data["changes"], partial=True)
        changes_serializer.is_valid(raise_exception=True)
        changes = changes_serializer.validated_data
        validate_images(request.user, changes)

        with transaction.atomic():
            user = User.objects.select_for_update().get(pk=request.user.pk)
            producer = Producer.objects.select_for_update().filter(user=user).first()
            if producer is None or not ProducerApplication.objects.filter(
                    producer=producer, pk=body.validated_data["application_id"]).exists():
                raise application_not_found()
            latest = latest_application(producer, lock=True)
            if latest.pk != body.validated_data["application_id"]:
                raise Conflict("APPLICATION_CONFLICT", "申請情報が更新されました。再取得してください。")
            if latest.status not in RESUBMITTABLE:
                raise Conflict("APPLICATION_NOT_RETURNED", "差し戻し・却下された申請のみ再申請できます。")
            ensure_producer_not_suspended(producer)

            apply_fields(producer, changes)
            producer.approval_status = Producer.ApprovalStatus.PENDING
            producer.save()
            reason = changes["application_reason"] if "application_reason" in changes else latest.application_reason
            application = ProducerApplication.objects.create(
                producer=producer, status=Status.PENDING, application_reason=reason or "",
                submitted_at=timezone.now())
        return accepted("修正内容を保存し、再申請を受け付けました。", producer, application)
