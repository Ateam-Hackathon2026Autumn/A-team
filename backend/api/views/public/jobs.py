"""求人（公開側・応募）

認証: 一覧・詳細は公開。応募・応募状況・取り下げは会員（未ログインは 401）。メール未確認でも使える
仕様: Notion の各API定義＋api-spec.md「7. 実装で決めたこと」ステップ9。カラム名: claude/er-diagram.md
公開条件: 求人が public かつ生産者が公開中（services/visibility.py の public_content）
応募できるかの判定は services/jobs.py（募集期間・採用枠・勤務日の空き）

実装済み:
  - 求人一覧: GET /api/v1/jobs
      ・areaId（勤務地の都道府県のエリア）・prefectureId・producerId・genre（生産者のジャンル）で絞り込み（AND）
      ・created_at・id の降順。募集期間外・採用枠がいっぱいの求人も出し、isAcceptingApplications で見分ける
  - 求人詳細: GET /api/v1/jobs/:jobId
      ・一覧の項目＋description・requirements・belongings・notes・applicationQuestions（空の配列）・hasApplied・workDates
      ・workDates は今日以降の勤務日（満員も含む）を日付順。workDatesPage・workDatesPageSize でページング
      ・公開対象外は 404 JOB_NOT_FOUND（募集期間外でも公開中なら見られる）
  - 応募: POST /api/v1/jobs/:jobId/applications（services/jobs.py の apply_for_job）。201 で応募
  - 応募状況: GET /api/v1/users/me/job-applications
      ・自分の応募を created_at・id の降順（すべての状態。status で絞り込み）。非公開になった求人は title が null
  - 取り下げ: POST /api/v1/users/me/job-applications/:applicationId/withdraw
      ・本文なし。applied・screening のときだけ（それ以外は 409 WITHDRAW_NOT_ALLOWED）。200 で応募状況の1件
      ・他人・存在しない応募は 404 APPLICATION_NOT_FOUND
"""
from django.db.models import Prefetch
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from marche.models import ApplicationWorkDate, Job, JobApplication

from ...common.exceptions import ApiError
from ...common.pagination import paginate, validate_query
from ...common.serializers import StrictSerializer
from ...serializers.public.jobs import (
    MAX_ID,
    JobApplicationCreateSerializer,
    JobApplicationSerializer,
    JobDetailQuerySerializer,
    JobDetailSerializer,
    JobListQuerySerializer,
    JobSummarySerializer,
    MyJobApplicationQuerySerializer,
    MyJobApplicationSerializer,
    WorkDateSerializer,
)
from ...services.jobs import (
    apply_for_job,
    has_room,
    job_not_found,
    with_acceptance,
    withdraw_application,
    work_dates_with_remaining,
)
from ...services.visibility import public_content


def public_jobs(today):
    return with_acceptance(public_content(Job.objects.all()), today).select_related("prefecture", "producer")


class JobListView(APIView):
    """GET /api/v1/jobs"""

    permission_classes = [AllowAny]

    def get(self, request):
        query = validate_query(JobListQuerySerializer, request)
        today = timezone.localdate()
        filters = {}
        if "area_id" in query:
            filters["prefecture__area_id"] = query["area_id"]
        if "prefecture_id" in query:
            filters["prefecture_id"] = query["prefecture_id"]
        if "producer_id" in query:
            filters["producer_id"] = query["producer_id"]
        if "genre" in query:
            filters["producer__genre"] = query["genre"]
        jobs = public_jobs(today).filter(**filters).order_by("-created_at", "-id")
        count = public_content(Job.objects.all()).filter(**filters)
        return Response(paginate(jobs, query, JobSummarySerializer, count_queryset=count, context={"today": today}))


class JobDetailView(APIView):
    """GET /api/v1/jobs/:jobId"""

    permission_classes = [AllowAny]

    def get(self, request, job_id):
        query = validate_query(JobDetailQuerySerializer, request)
        today = timezone.localdate()
        job = public_jobs(today).filter(pk=job_id).first() if job_id <= MAX_ID else None
        if job is None:
            raise job_not_found()
        has_applied = (request.user.is_authenticated
                       and JobApplication.objects.filter(job=job, user=request.user).exists())
        body = JobDetailSerializer(job, context={"today": today, "has_applied": has_applied}).data
        page_query = {"page": query["work_dates_page"], "page_size": query["work_dates_page_size"]}
        body["work_dates"] = paginate(work_dates_with_remaining(job, today), page_query, WorkDateSerializer,
                                      context={"job_has_room": has_room(job, today)})
        return Response(body)


class JobApplicationCreateView(APIView):
    """POST /api/v1/jobs/:jobId/applications"""

    permission_classes = [IsAuthenticated]

    def post(self, request, job_id):
        serializer = JobApplicationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if job_id > MAX_ID:
            raise job_not_found()
        application = apply_for_job(job_id, request.user, serializer.validated_data)
        application = JobApplication.objects.prefetch_related("application_work_dates").get(pk=application.pk)
        return Response(JobApplicationSerializer(application).data, status=status.HTTP_201_CREATED)


def my_applications(user):
    dates = ApplicationWorkDate.objects.select_related("work_date")
    return (JobApplication.objects.filter(user=user).select_related("job")
            .prefetch_related(Prefetch("application_work_dates", queryset=dates)))


def my_context(user):
    public_ids = set(public_content(Job.objects.filter(job_applications__user=user)).values_list("id", flat=True))
    return {"public_job_ids": public_ids}


class MyJobApplicationListView(APIView):
    """GET /api/v1/users/me/job-applications"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = validate_query(MyJobApplicationQuerySerializer, request)
        applications = JobApplication.objects.filter(user=request.user)
        items = my_applications(request.user)
        if "status" in query:
            applications = applications.filter(status=query["status"])
            items = items.filter(status=query["status"])
        return Response(paginate(items.order_by("-created_at", "-id"), query, MyJobApplicationSerializer,
                                 count_queryset=applications, context=my_context(request.user)))


class MyJobApplicationWithdrawView(APIView):
    """POST /api/v1/users/me/job-applications/:applicationId/withdraw"""

    permission_classes = [IsAuthenticated]

    def post(self, request, application_id):
        StrictSerializer(data=request.data or {}).is_valid(raise_exception=True)  # 本文は受け付けない
        if application_id > MAX_ID:
            raise ApiError(status.HTTP_404_NOT_FOUND, "APPLICATION_NOT_FOUND", "応募が見つかりません。")
        withdraw_application(application_id, request.user)
        application = my_applications(request.user).get(pk=application_id)
        return Response(MyJobApplicationSerializer(application, context=my_context(request.user)).data)
