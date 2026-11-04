"""生産者ダッシュボードの求人管理・採用View"""

from django.db import transaction
from django.db.models import Q, Count
from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    ValidationError,
    NotFound,
)

from marche.models import (
    Job,
    JobWorkDate,
    JobApplication,
    ApplicationWorkDate,
    Prefecture,
    Notification,
)

from api.serializers.dashboard.jobs import (
    JobListQuerySerializer,
    JobListSerializer,
    JobCreateSerializer,
    JobDetailSerializer,
    JobUpdateSerializer,
    JobApplicationListQuerySerializer,
    JobApplicationSerializer,
    JobApplicationStatusUpdateSerializer,
)

from api.common.permissions import (
    IsApprovedProducer,
    ensure_producer_not_suspended,
)

from api.services.notifications import notify


# ============================================================
# 共通エラー
# ============================================================

class Conflict(APIException):
    """状態競合エラー"""

    status_code = status.HTTP_409_CONFLICT
    default_code = "CONFLICT"
    default_detail = "現在の状態ではこの操作を実行できません。"


# ============================================================
# 共通処理
# ============================================================

def get_producer(request):
    """ログイン中のユーザーに紐づく生産者を取得する"""

    try:
        return request.user.producer
    except Exception:
        raise NotFound("生産者情報が見つかりません。")


def validate_query(serializer_class, query_params):
    """クエリパラメータを検証する"""

    serializer = serializer_class(data=query_params)
    serializer.is_valid(raise_exception=True)

    return serializer.validated_data


def paginate(queryset, page, page_size):
    """一覧データをページネーションする"""

    total = queryset.count()

    start = (page - 1) * page_size
    end = start + page_size

    items = queryset[start:end]

    total_pages = (
        (total + page_size - 1) // page_size
        if total
        else 0
    )

    return {
        "items": items,
        "total": total,
        "page": page,
        "pageSize": page_size,
        "totalPages": total_pages,
    }


def get_owned_job(producer, job_id, lock=False):
    """ログイン中の生産者が所有する求人を取得する"""

    queryset = Job.objects.filter(
        id=job_id,
        producer=producer,
    )

    if lock:
        queryset = queryset.select_for_update()

    job = queryset.first()

    if not job:
        raise NotFound("求人が見つかりません。")

    return job


def validate_prefecture(producer, data):
    """都道府県を検証する"""

    prefecture_id = data.pop(
        "prefecture_id",
        producer.prefecture_id,
    )

    if not prefecture_id:
        raise ValidationError({
            "prefecture_id": [
                "都道府県を指定してください。"
            ]
        })

    if not Prefecture.objects.filter(
        id=prefecture_id
    ).exists():
        raise ValidationError({
            "prefecture_id": [
                "指定された都道府県が存在しません。"
            ]
        })

    return prefecture_id


def validate_job_period(job, work_dates):
    """勤務日が求人の募集期間内か検証する"""

    for index, item in enumerate(work_dates):

        work_date = item["work_date"]

        if (
            job.period_start
            and work_date < job.period_start
        ):
            raise ValidationError({
                "work_dates": {
                    index: {
                        "work_date": [
                            "勤務日は募集開始日以降にしてください。"
                        ]
                    }
                }
            })

        if (
            job.period_end
            and work_date > job.period_end
        ):
            raise ValidationError({
                "work_dates": {
                    index: {
                        "work_date": [
                            "勤務日は募集終了日以前にしてください。"
                        ]
                    }
                }
            })


def validate_publication_work_dates(job, work_dates):
    """公開状態と勤務日の条件を検証する"""

    if job.term_type == "long":
        if work_dates:
            raise ValidationError({
                "work_dates": [
                    "長期求人には勤務日を登録できません。"
                ]
            })

        return

    if job.publish_status != "public":
        return

    today = timezone.localdate()

    future_dates = [
        item["work_date"]
        for item in work_dates
        if item["work_date"] >= today
    ]

    if not future_dates:
        raise ValidationError({
            "work_dates": [
                "公開する単発・短期求人には今日以降の勤務日を1日以上登録してください。"
            ]
        })


def update_job_work_dates(job, work_dates):
    """
    勤務日を更新する。

    ・idあり：既存勤務日を更新
    ・idなし：新規勤務日を登録
    ・送信されなかった既存勤務日：削除

    ただし、応募者が希望している勤務日は削除できない。
    """

    existing_dates = {
        item.id: item
        for item in job.job_work_dates.select_for_update()
    }

    submitted_ids = set()

    for item in work_dates:

        work_date_id = item.get("id")

        if work_date_id:

            work_date = existing_dates.get(
                work_date_id
            )

            if not work_date:
                raise ValidationError({
                    "work_dates": [
                        "指定された勤務日がこの求人に存在しません。"
                    ]
                })

            submitted_ids.add(work_date_id)

            # 応募者が希望している勤務日の変更は禁止
            if (
                work_date.work_date != item["work_date"]
                and work_date.application_work_dates.exists()
            ):
                raise Conflict({
                    "code": "WORK_DATE_HAS_APPLICATIONS",
                    "message": "応募者がいる勤務日は変更できません。",
                })

            work_date.work_date = item["work_date"]
            work_date.needed_count = item["needed_count"]

            work_date.save(
                update_fields=[
                    "work_date",
                    "needed_count",
                    "updated_at",
                ]
            )

        else:

            JobWorkDate.objects.create(
                job=job,
                work_date=item["work_date"],
                needed_count=item["needed_count"],
            )

    # 送信されなかった勤務日を削除
    delete_ids = (
        set(existing_dates.keys()) - submitted_ids
    )

    for work_date_id in delete_ids:

        work_date = existing_dates[work_date_id]

        if work_date.application_work_dates.exists():
            raise Conflict({
                "code": "WORK_DATE_HAS_APPLICATIONS",
                "message": "応募者が希望している勤務日は削除できません。",
            })

        work_date.delete()


def get_job_work_dates(job):
    """求人の勤務日を取得する"""

    return list(
        job.job_work_dates.order_by("work_date")
    )


def get_application_with_related(application_id, job):
    """求人に紐づく応募者を取得する"""

    application = (
        JobApplication.objects
        .select_related("user", "job")
        .filter(
            id=application_id,
            job=job,
        )
        .first()
    )

    if not application:
        raise NotFound("応募者が見つかりません。")

    return application


def get_hired_count(job):
    """採用済み人数を取得する"""

    return JobApplication.objects.filter(
        job=job,
        status=JobApplication.Status.HIRED,
    ).count()


# ============================================================
# 求人一覧・登録
# GET  /api/v1/dashboard/jobs
# POST /api/v1/dashboard/jobs
# ============================================================

class JobListCreateView(APIView):

    permission_classes = [
        IsApprovedProducer,
    ]

    def get(self, request):

        producer = get_producer(request)

        query = validate_query(
            JobListQuerySerializer,
            request.query_params,
        )

        queryset = Job.objects.filter(
            producer=producer,
        )

        publish_status = query.get(
            "publish_status"
        )

        keyword = query.get(
            "keyword",
            "",
        )

        if publish_status:
            queryset = queryset.filter(
                publish_status=publish_status
            )

        if keyword:
            queryset = queryset.filter(
                Q(title__icontains=keyword)
                | Q(description__icontains=keyword)
            )

        queryset = queryset.order_by(
            "-created_at",
            "-id",
        )

        result = paginate(
            queryset,
            query["page"],
            query["page_size"],
        )

        serializer = JobListSerializer(
            result["items"],
            many=True,
        )

        return Response({
            "items": serializer.data,
            "total": result["total"],
            "page": result["page"],
            "pageSize": result["pageSize"],
            "totalPages": result["totalPages"],
        })

    def post(self, request):

        producer = get_producer(request)

        # 掲載停止中の生産者は登録不可
        ensure_producer_not_suspended(producer)

        serializer = JobCreateSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        data = dict(serializer.validated_data)

        work_dates = data.pop(
            "work_dates",
            [],
        )

        prefecture_id = validate_prefecture(
            producer,
            data,
        )

        with transaction.atomic():

            job = Job.objects.create(
                producer=producer,
                prefecture_id=prefecture_id,
                **data,
            )

            validate_publication_work_dates(
                job,
                work_dates,
            )

            validate_job_period(
                job,
                work_dates,
            )

            for item in work_dates:

                JobWorkDate.objects.create(
                    job=job,
                    work_date=item["work_date"],
                    needed_count=item["needed_count"],
                )

        job = (
            Job.objects
            .prefetch_related("job_work_dates")
            .get(id=job.id)
        )

        response_serializer = JobDetailSerializer(
            job
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
        )


# ============================================================
# 求人詳細・更新・削除
# GET    /api/v1/dashboard/jobs/:jobId
# PATCH  /api/v1/dashboard/jobs/:jobId
# DELETE /api/v1/dashboard/jobs/:jobId
# ============================================================

class JobDetailView(APIView):

    permission_classes = [
        IsApprovedProducer,
    ]

    def get(self, request, job_id):

        producer = get_producer(request)

        job = get_owned_job(
            producer,
            job_id,
        )

        job = (
            Job.objects
            .prefetch_related("job_work_dates")
            .get(
                id=job.id,
                producer=producer,
            )
        )

        serializer = JobDetailSerializer(
            job
        )

        return Response(serializer.data)

    def patch(self, request, job_id):

        producer = get_producer(request)

        ensure_producer_not_suspended(producer)

        with transaction.atomic():

            job = get_owned_job(
                producer,
                job_id,
                lock=True,
            )

            serializer = JobUpdateSerializer(
                job,
                data=request.data,
                partial=True,
            )

            serializer.is_valid(
                raise_exception=True
            )

            data = dict(
                serializer.validated_data
            )

            work_dates_supplied = (
                "work_dates" in data
            )

            work_dates = data.pop(
                "work_dates",
                None,
            )

            prefecture_id = None

            if "prefecture_id" in data:
                prefecture_id = validate_prefecture(
                    producer,
                    data,
                )

            # 求人情報を更新
            for key, value in data.items():
                setattr(job, key, value)

            if prefecture_id is not None:
                job.prefecture_id = prefecture_id

            job.save()

            # 勤務日が送られてきた場合は更新
            if work_dates_supplied:

                validate_publication_work_dates(
                    job,
                    work_dates,
                )

                validate_job_period(
                    job,
                    work_dates,
                )

                update_job_work_dates(
                    job,
                    work_dates,
                )

            else:

                # 勤務日が省略された場合は既存勤務日で検証
                existing_dates = [
                    {
                        "work_date": item.work_date,
                    }
                    for item in get_job_work_dates(job)
                ]

                validate_publication_work_dates(
                    job,
                    existing_dates,
                )

                validate_job_period(
                    job,
                    existing_dates,
                )

            job = (
                Job.objects
                .prefetch_related("job_work_dates")
                .get(id=job.id)
            )

        response_serializer = JobDetailSerializer(
            job
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_200_OK,
        )

    def delete(self, request, job_id):

        producer = get_producer(request)

        ensure_producer_not_suspended(producer)

        with transaction.atomic():

            job = get_owned_job(
                producer,
                job_id,
                lock=True,
            )

            # 応募履歴がある求人は削除できない
            if JobApplication.objects.filter(
                job=job
            ).exists():

                raise Conflict({
                    "code": "JOB_HAS_APPLICATIONS",
                    "message": "応募履歴がある求人は削除できません。非公開にしてください。",
                })

            job.delete()

        return Response(
            status=status.HTTP_204_NO_CONTENT
        )


# ============================================================
# 応募者一覧
# GET /api/v1/dashboard/jobs/:jobId/applications
# ============================================================

class JobApplicationListView(APIView):

    permission_classes = [
        IsApprovedProducer,
    ]

    def get(self, request, job_id):

        producer = get_producer(request)

        job = get_owned_job(
            producer,
            job_id,
        )

        query = validate_query(
            JobApplicationListQuerySerializer,
            request.query_params,
        )

        queryset = (
            JobApplication.objects
            .filter(job=job)
            .select_related("user")
            .prefetch_related(
                "application_work_dates__work_date"
            )
        )

        application_status = query.get(
            "status"
        )

        if application_status:
            queryset = queryset.filter(
                status=application_status
            )

        queryset = queryset.order_by(
            "-created_at",
            "-id",
        )

        result = paginate(
            queryset,
            query["page"],
            query["page_size"],
        )

        serializer = JobApplicationSerializer(
            result["items"],
            many=True,
        )

        return Response({
            "items": serializer.data,
            "total": result["total"],
            "page": result["page"],
            "pageSize": result["pageSize"],
            "totalPages": result["totalPages"],
        })


# ============================================================
# 採用・不採用・選考中・勤務完了
# PATCH /api/v1/dashboard/jobs/:jobId/applications/:applicationId
# ============================================================

class JobApplicationDetailView(APIView):

    permission_classes = [
        IsApprovedProducer,
    ]

    def patch(
        self,
        request,
        job_id,
        application_id,
    ):

        producer = get_producer(request)

        ensure_producer_not_suspended(producer)

        serializer = JobApplicationStatusUpdateSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        new_status = serializer.validated_data[
            "status"
        ]

        notification_data = None

        with transaction.atomic():

            job = get_owned_job(
                producer,
                job_id,
                lock=True,
            )

            application = (
                JobApplication.objects
                .select_for_update()
                .select_related("user", "job")
                .filter(
                    id=application_id,
                    job=job,
                )
                .first()
            )

            if not application:
                raise NotFound(
                    "応募者が見つかりません。"
                )

            current_status = application.status

            # 状態遷移ルール
            allowed_transitions = {
                JobApplication.Status.APPLIED: [
                    JobApplication.Status.SCREENING,
                    JobApplication.Status.HIRED,
                    JobApplication.Status.REJECTED,
                ],
                JobApplication.Status.SCREENING: [
                    JobApplication.Status.HIRED,
                    JobApplication.Status.REJECTED,
                ],
                JobApplication.Status.HIRED: [],
                JobApplication.Status.REJECTED: [],
                JobApplication.Status.WITHDRAWN: [],
                JobApplication.Status.COMPLETED: [],
            }

            # 長期求人の採用済み応募者のみ勤務完了にできる
            if (
                current_status == JobApplication.Status.HIRED
                and new_status == JobApplication.Status.COMPLETED
                and job.term_type == "long"
            ):
                allowed_transitions[
                    JobApplication.Status.HIRED
                ].append(
                    JobApplication.Status.COMPLETED
                )

            if new_status not in allowed_transitions.get(
                current_status,
                [],
            ):
                raise Conflict({
                    "code": "INVALID_APPLICATION_STATUS_TRANSITION",
                    "message": "現在の応募状態から指定された状態には変更できません。",
                })

            application.status = new_status

            # 採用・不採用の決定日時
            if new_status in [
                JobApplication.Status.HIRED,
                JobApplication.Status.REJECTED,
            ]:
                application.decided_at = timezone.now()

            application.save(
                update_fields=[
                    "status",
                    "decided_at",
                    "updated_at",
                ]
            )

            # 採用・不採用の場合だけ通知する
            if new_status in [
                JobApplication.Status.HIRED,
                JobApplication.Status.REJECTED,
            ]:

                if new_status == JobApplication.Status.HIRED:

                    title = "求人への応募結果のお知らせ"

                    body = (
                        f"ご応募いただいた求人「{job.title}」について、"
                        "採用が決定しました。\n"
                        "詳細については、マイページをご確認ください。"
                    )

                else:

                    title = "求人への応募結果のお知らせ"

                    body = (
                        f"ご応募いただいた求人「{job.title}」について、"
                        "今回は採用を見送らせていただくことになりました。\n"
                        "ご応募いただきありがとうございました。"
                    )

                notification_data = {
                    "user": application.user,
                    "title": title,
                    "body": body,
                }

            # 採用人数の集計
            hired_count = get_hired_count(job)

            slots = job.slots

            is_over_capacity = (
                hired_count > slots
            )

        # 通知はトランザクション内で登録する
        # notify() 内でメールは transaction.on_commit により送信される
        if notification_data:

            notify(
                user=notification_data["user"],
                notification_type=(
                    Notification.NotificationType.APPLICATION_RESULT
                ),
                title=notification_data["title"],
                body=notification_data["body"],
                link_path="/mypage/applications",
            )

        response_data = {
            "id": application.id,
            "status": application.status,
            "decided_at": application.decided_at,
            "hired_count": hired_count,
            "slots": slots,
            "is_over_capacity": is_over_capacity,
        }

        return Response(
            response_data,
            status=status.HTTP_200_OK,
        )
    

# """求人管理・採用

# 認証: 生産者
# 共通: 生産者APIの共通チェック（approved でなければ 403、掲載停止中にできない操作は 409）は common/permissions.py

# このファイルに書くもの（APIView / generics のクラス）。シーケンス図は Notion の同名の図:
#   - 求人一覧（生産者）: GET /api/v1/dashboard/jobs
#   - 求人登録: POST /api/v1/dashboard/jobs
#       ・勤務日の配列も登録。long は勤務日なし、one_day・short の公開には今日以降の勤務日1日以上。画像は任意
#   - 求人詳細（生産者）: GET /api/v1/dashboard/jobs/:jobId
#   - 求人更新: PATCH /api/v1/dashboard/jobs/:jobId
#       ・勤務日は既存分を id 付きで送り、送られなかったものは削除。希望者がいる勤務日の削除は 409
#   - 求人削除: DELETE /api/v1/dashboard/jobs/:jobId
#       ・応募されたことがあれば 409（非公開にしてもらう）
#   - 求人応募者一覧: GET /api/v1/dashboard/jobs/:jobId/applications
#       ・status で絞り込み。氏名・電話・年齢（birth_date から計算）・message・answers・希望日。生年月日とメールは返さない
#   - 採用・不採用: PATCH /api/v1/dashboard/jobs/:jobId/applications/:applicationId
#       ・applied→screening・hired・rejected、screening→hired・rejected、長期の hired→completed
#       ・hired・rejected は戻せない。hired・rejected のときだけ応募者に通知・定型文メール
#       ・募集人数を超えても採用可（超えているかを返す）

# 仕様: claude/api-spec.md / カラム名: claude/er-diagram.md
# """
