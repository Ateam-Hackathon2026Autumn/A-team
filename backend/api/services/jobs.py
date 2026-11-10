"""求人の応募（応募できるかの判定・応募・取り下げ）

view から呼ぶ業務ロジック。公開側の一覧・詳細・応募・応募状況で同じ判定を使う。

応募できるか（isAcceptingApplications）は、次の3つをすべて満たすとき:
  1. 募集期間内（period_start〜period_end。日本時間の日付で両端を含む。空の側は無制限）
  2. 採用済み（hired・completed）の人数が募集人数（slots）未満。応募中・選考中の人は枠を使わない
  3. 勤務日がある求人は、今日以降で空きのある勤務日が1日以上ある
     勤務日の空き＝その日の募集人数（needed_count）− その日を希望して採用された人数

実装済み:
  - with_acceptance(queryset, today): 求人の QuerySet に判定用の値（hired_count・has_work_dates・has_open_work_date）を
    サブクエリで付ける（一覧で N+1 にしない）
  - is_accepting(job, today): 判定（with_acceptance を付けた求人に使う）
  - work_dates_with_remaining(job, today): 今日以降の勤務日に hired_count を付けた QuerySet（日付・id の順）
  - apply_for_job(job_id, user, data): 応募（1つのトランザクション。求人の行をロックしてから確かめる）
      公開中でない → 404 JOB_NOT_FOUND／自分の求人 → 409 CANNOT_APPLY_OWN／応募済み（状態に関係なく）→ 409 ALREADY_APPLIED／
      応募できない → 409 JOB_NOT_ACCEPTING／勤務日の指定がおかしい → 400／選んだ日が過去・満員 → 409 WORK_DATE_UNAVAILABLE
      status=applied で作り、希望日を application_work_dates に保存。生産者に通知・メール（new_application）、応募者にメール
  - withdraw_application(application_id, user): 取り下げ。applied・screening のときだけ withdrawn（それ以外は
      409 WITHDRAW_NOT_ALLOWED）。生産者に通知・メール（application_withdrawn）

使う場所: api/views/public/jobs.py、api/serializers/public/jobs.py
"""
from django.db import IntegrityError, transaction
from django.db.models import Count, Exists, F, IntegerField, OuterRef, Subquery, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework import serializers, status

from marche.models import ApplicationWorkDate, Job, JobApplication, JobWorkDate, Notification

from ..common.exceptions import ApiError, Conflict
from . import mail
from .notifications import notify
from .visibility import public_content

HIRED_STATUSES = [JobApplication.Status.HIRED, JobApplication.Status.COMPLETED]
WITHDRAWABLE_STATUSES = [JobApplication.Status.APPLIED, JobApplication.Status.SCREENING]
PRODUCER_APPLICANTS_PATH = "/dashboard/jobs/{job_id}/applicants"


def job_not_found():
    return ApiError(status.HTTP_404_NOT_FOUND, "JOB_NOT_FOUND", "求人が見つかりません。")


def date_hired_count(work_date_ref):
    """勤務日ごとの採用済みの人数（サブクエリ）"""
    hired = (ApplicationWorkDate.objects.filter(work_date=work_date_ref, application__status__in=HIRED_STATUSES)
             .order_by().values("work_date").annotate(c=Count("id")).values("c")[:1])
    return Coalesce(Subquery(hired, output_field=IntegerField()), Value(0))


def with_acceptance(queryset, today):
    job_hired = (JobApplication.objects.filter(job=OuterRef("pk"), status__in=HIRED_STATUSES)
                 .order_by().values("job").annotate(c=Count("id")).values("c")[:1])
    open_dates = (JobWorkDate.objects.filter(job=OuterRef("pk"), work_date__gte=today)
                  .annotate(hired=date_hired_count(OuterRef("pk"))).filter(needed_count__gt=F("hired")))
    return queryset.annotate(
        hired_count=Coalesce(Subquery(job_hired, output_field=IntegerField()), Value(0)),
        has_work_dates=Exists(JobWorkDate.objects.filter(job=OuterRef("pk"))),
        has_open_work_date=Exists(open_dates),
    )


def in_period(job, today):
    return (job.period_start is None or job.period_start <= today) and (job.period_end is None or today <= job.period_end)


def has_room(job, today):
    """募集期間内で、全体の採用枠に空きがある"""
    return in_period(job, today) and job.hired_count < job.slots


def is_accepting(job, today):
    return has_room(job, today) and (not job.has_work_dates or job.has_open_work_date)


def work_dates_with_remaining(job, today):
    return (JobWorkDate.objects.filter(job=job, work_date__gte=today)
            .annotate(hired_count=date_hired_count(OuterRef("pk"))).order_by("work_date", "id"))


def apply_for_job(job_id, user, data):
    """応募を作って返す。data は JobApplicationCreateSerializer の validated_data"""
    today = timezone.localdate()
    with transaction.atomic():
        job = Job.objects.select_for_update().filter(pk=job_id).select_related("producer__user").first()
        if job is None or not public_content(Job.objects.filter(pk=job_id)).exists():
            raise job_not_found()
        if job.producer.user_id == user.pk:
            raise Conflict("CANNOT_APPLY_OWN", "ご自身の求人には応募できません。")
        if JobApplication.objects.filter(job=job, user=user).exists():
            raise Conflict("ALREADY_APPLIED", "この求人にはすでに応募しています。")
        job = with_acceptance(Job.objects.filter(pk=job.pk), today).select_related("producer__user").get()
        if not is_accepting(job, today):
            raise Conflict("JOB_NOT_ACCEPTING", "この求人は現在、応募を受け付けていません。")

        date_ids = sorted(set(data["work_date_ids"]))
        if job.has_work_dates and not date_ids:
            raise serializers.ValidationError({"work_date_ids": ["希望する勤務日を1日以上選んでください。"]})
        if not job.has_work_dates and date_ids:
            raise serializers.ValidationError({"work_date_ids": ["この求人は勤務日を選べません。"]})
        dates = list(JobWorkDate.objects.filter(job=job, pk__in=date_ids)
                     .annotate(hired_count=date_hired_count(OuterRef("pk"))))
        if len(dates) != len(date_ids):
            raise serializers.ValidationError({"work_date_ids": ["この求人の勤務日ではない日が含まれています。"]})
        if any(d.work_date < today or d.hired_count >= d.needed_count for d in dates):
            raise Conflict("WORK_DATE_UNAVAILABLE", "選んだ勤務日のなかに、過去の日か募集が埋まった日があります。")

        try:
            with transaction.atomic():
                application = JobApplication.objects.create(
                    job=job, user=user, message=data.get("message"), answers=[],
                    status=JobApplication.Status.APPLIED)
        except IntegrityError:  # 同じ人の応募が同時に来た
            raise Conflict("ALREADY_APPLIED", "この求人にはすでに応募しています。")
        ApplicationWorkDate.objects.bulk_create([
            ApplicationWorkDate(application=application, work_date=d) for d in sorted(dates, key=lambda d: d.pk)])
        _notify_applied(job, application, user, dates)
    return application


def _dates_text(dates):
    if not dates:
        return ""
    return "希望日：" + "、".join(d.work_date.strftime("%Y年%m月%d日") for d in sorted(dates, key=lambda d: d.work_date)) + "\n"


def _notify_applied(job, application, user, dates):
    name = f"{user.last_name} {user.first_name}".strip()
    notify(job.producer.user, Notification.NotificationType.NEW_APPLICATION, "新しい応募がありました",
           f"「{job.title}」に{name}さんから応募がありました。\n{_dates_text(dates)}\n"
           "応募者一覧の画面で内容を確認し、選考を進めてください。\n",
           PRODUCER_APPLICANTS_PATH.format(job_id=job.id))
    body = (f"{name} 様\n\n「{job.title}」（{job.producer.business_name}）への応募を受け付けました。\n"
            f"{_dates_text(dates)}\n選考の結果は、生産者から通知とメールでお知らせします。\n")
    email = user.email
    transaction.on_commit(lambda: mail.send(email, "求人への応募を受け付けました", body))


def withdraw_application(application_id, user):
    """自分の応募を取り下げて返す。他人・存在しない応募は 404 APPLICATION_NOT_FOUND"""
    with transaction.atomic():
        found = JobApplication.objects.filter(pk=application_id, user=user).values("job_id").first()
        if found is None:
            raise ApiError(status.HTTP_404_NOT_FOUND, "APPLICATION_NOT_FOUND", "応募が見つかりません。")
        job = Job.objects.select_for_update().select_related("producer__user").get(pk=found["job_id"])
        application = JobApplication.objects.select_for_update().get(pk=application_id)
        if application.status not in WITHDRAWABLE_STATUSES:
            raise Conflict("WITHDRAW_NOT_ALLOWED", "この応募は取り下げられません。生産者にメッセージでご連絡ください。")
        application.status = JobApplication.Status.WITHDRAWN
        application.save(update_fields=["status", "updated_at"])
        name = f"{user.last_name} {user.first_name}".strip()
        notify(job.producer.user, Notification.NotificationType.APPLICATION_WITHDRAWN, "応募が取り下げられました",
               f"「{job.title}」への{name}さんの応募が取り下げられました。\n",
               PRODUCER_APPLICANTS_PATH.format(job_id=job.id))
    return application
