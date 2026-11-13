"""求人（公開側・応募） のシリアライザー

使う view: api/views/public/jobs.py

実装済み:
  - JobListQuerySerializer: 一覧のクエリ（page・pageSize・areaId・prefectureId・producerId・genre）
  - JobSummarySerializer: 一覧の1件
      {id, title, producer: {id, businessName, genre}, prefectureId, prefectureName, areaId, termType, payUnit, payAmount,
       periodStart, periodEnd, workHours, workPlace, slots, inexperiencedOk, coverImageUrl, isAcceptingApplications}
      services/jobs.py の with_acceptance を付けた求人に使う。context["today"] を渡す
  - JobDetailQuerySerializer: 詳細のクエリ（workDatesPage・workDatesPageSize）
  - JobDetailSerializer: 詳細。一覧の項目＋description・requirements・belongings・notes・applicationQuestions（空の配列）・
      hasApplied（ログイン中に応募済みか。context["has_applied"]）。workDates は view が足す
  - WorkDateSerializer: 勤務日1件 {id, workDate, neededCount, remainingCount, isSelectable}。context["job_has_room"]
  - JobApplicationCreateSerializer: 応募の本文 {workDateIds, message, answers（空の配列だけ）, requirementsConfirmed}
  - JobApplicationSerializer: 応募（201）のレスポンス {id, jobId, workDateIds, message, answers, status, decidedAt, createdAt}
  - MyJobApplicationQuerySerializer / MyJobApplicationSerializer: 応募状況の1件
      {id, job: {id, title, isPublic}, workDates: [{id, workDate}], status, withdrawable, decidedAt, createdAt, updatedAt}
      context["public_job_ids"] を渡す

入力エラーは 400（項目ごとのメッセージ）。カラム名は claude/er-diagram.md に合わせる
"""
from rest_framework import serializers

from marche.models import Job, JobApplication, JobWorkDate, Producer

from ...common.images import ImageUrlField
from ...common.pagination import PageQuerySerializer
from ...common.serializers import QuerySerializer, StrictSerializer
from ...services.jobs import WITHDRAWABLE_STATUSES, is_accepting

MAX_ID = 2 ** 63 - 1
MAX_WORK_DATES = 100


class JobListQuerySerializer(PageQuerySerializer):
    area_id = serializers.IntegerField(required=False, min_value=1, max_value=MAX_ID)
    prefecture_id = serializers.IntegerField(required=False, min_value=1, max_value=MAX_ID)
    producer_id = serializers.IntegerField(required=False, min_value=1, max_value=MAX_ID)
    genre = serializers.ChoiceField(choices=Producer.Genre.choices, required=False)


class JobProducerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Producer
        fields = ["id", "business_name", "genre"]


class JobSummarySerializer(serializers.ModelSerializer):
    producer = JobProducerSerializer()
    prefecture_name = serializers.CharField(source="prefecture.name")
    area_id = serializers.IntegerField(source="prefecture.area_id")
    cover_image_url = ImageUrlField(source="cover_image")
    is_accepting_applications = serializers.SerializerMethodField()

    class Meta:
        model = Job
        fields = ["id", "title", "producer", "prefecture_id", "prefecture_name", "area_id", "term_type", "pay_unit",
                  "pay_amount", "period_start", "period_end", "work_hours", "work_place", "slots", "inexperienced_ok",
                  "cover_image_url", "is_accepting_applications"]

    def get_is_accepting_applications(self, job):
        return is_accepting(job, self.context["today"])


class JobDetailQuerySerializer(QuerySerializer):
    work_dates_page = serializers.IntegerField(required=False, default=1, min_value=1, max_value=1_000_000)
    work_dates_page_size = serializers.IntegerField(required=False, default=20, min_value=1, max_value=100)


class JobDetailSerializer(JobSummarySerializer):
    application_questions = serializers.SerializerMethodField()
    has_applied = serializers.SerializerMethodField()

    class Meta(JobSummarySerializer.Meta):
        fields = JobSummarySerializer.Meta.fields + [
            "description", "requirements", "belongings", "notes", "application_questions", "has_applied"]

    def get_application_questions(self, job):
        return []  # 質問を保存する場所が DB にないため（Notion どおり）

    def get_has_applied(self, job):
        return self.context.get("has_applied", False)


class WorkDateSerializer(serializers.ModelSerializer):
    """勤務日。hired_count を annotate しておく"""

    remaining_count = serializers.SerializerMethodField()
    is_selectable = serializers.SerializerMethodField()

    class Meta:
        model = JobWorkDate
        fields = ["id", "work_date", "needed_count", "remaining_count", "is_selectable"]

    def get_remaining_count(self, work_date):
        return max(work_date.needed_count - work_date.hired_count, 0)

    def get_is_selectable(self, work_date):
        return self.context["job_has_room"] and work_date.hired_count < work_date.needed_count


class JobApplicationCreateSerializer(StrictSerializer):
    work_date_ids = serializers.ListField(child=serializers.IntegerField(min_value=1, max_value=MAX_ID),
                                          max_length=MAX_WORK_DATES)
    message = serializers.CharField(max_length=2000, required=False, allow_null=True, allow_blank=True)
    answers = serializers.ListField(required=False, max_length=0, default=list)
    requirements_confirmed = serializers.BooleanField()

    def validate_work_date_ids(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError("同じ勤務日が重複しています。")
        return value

    def validate_message(self, value):
        return value or None

    def validate_requirements_confirmed(self, value):
        if value is not True:
            raise serializers.ValidationError("応募条件の確認が必要です。")
        return value


class JobApplicationSerializer(serializers.ModelSerializer):
    work_date_ids = serializers.SerializerMethodField()

    class Meta:
        model = JobApplication
        fields = ["id", "job_id", "work_date_ids", "message", "answers", "status", "decided_at", "created_at"]

    def get_work_date_ids(self, application):
        return sorted(item.work_date_id for item in application.application_work_dates.all())


class MyJobApplicationQuerySerializer(PageQuerySerializer):
    status = serializers.ChoiceField(choices=JobApplication.Status.choices, required=False)


class MyJobApplicationSerializer(serializers.ModelSerializer):
    """応募状況の1件。job を select_related、application_work_dates__work_date を prefetch しておく"""

    job = serializers.SerializerMethodField()
    work_dates = serializers.SerializerMethodField()
    withdrawable = serializers.SerializerMethodField()

    class Meta:
        model = JobApplication
        fields = ["id", "job", "work_dates", "status", "withdrawable", "decided_at", "created_at", "updated_at"]

    def get_job(self, application):
        is_public = application.job_id in self.context["public_job_ids"]
        return {"id": application.job_id, "title": application.job.title if is_public else None,
                "is_public": is_public}

    def get_work_dates(self, application):
        dates = sorted((item.work_date for item in application.application_work_dates.all()),
                       key=lambda d: (d.work_date, d.id))
        return [{"id": d.id, "work_date": d.work_date.isoformat()} for d in dates]

    def get_withdrawable(self, application):
        return application.status in WITHDRAWABLE_STATUSES
