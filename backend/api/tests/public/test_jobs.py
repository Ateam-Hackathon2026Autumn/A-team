"""求人（公開側・応募） のテスト

テスト対象: api/views/public/jobs.py（services/jobs.py）
  - 求人一覧・詳細: GET /api/v1/jobs・GET /api/v1/jobs/:jobId
  - 応募: POST /api/v1/jobs/:jobId/applications
  - 応募状況・取り下げ: GET /api/v1/users/me/job-applications・POST .../:applicationId/withdraw
"""
from datetime import timedelta

from django.core import mail
from django.utils import timezone

from marche.models import Area, ApplicationWorkDate, JobApplication, Notification, Prefecture, Producer, PublishStatus

from ..utils import (
    ApiTestCase,
    make_job,
    make_job_application,
    make_producer,
    make_user,
    make_work_date,
)

URL = "/api/v1/jobs"
MY_URL = "/api/v1/users/me/job-applications"


def today_plus(days):
    return timezone.localdate() + timedelta(days=days)


class JobListTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.producer = make_producer(business_name="山田農園")

    def items(self, res):
        return {item["id"]: item for item in res.json()["items"]}

    def test_list_and_accepting_flags(self):
        open_job = make_job(self.producer, title="受付中")
        make_work_date(open_job, days=3)
        ended = make_job(self.producer, period_end=today_plus(-1))
        future = make_job(self.producer, period_start=today_plus(1))
        full = make_job(self.producer, slots=1)
        make_job_application(full, status="hired")
        dates_full = make_job(self.producer)
        date = make_work_date(dates_full, days=3, needed_count=1)
        make_job_application(dates_full, status="hired", work_dates=[date])
        past_dates = make_job(self.producer)
        make_work_date(past_dates, days=-1)
        long_job = make_job(self.producer, term_type="long", period_end=today_plus(0))  # 今日まで（両端を含む）
        make_job(self.producer, publish_status=PublishStatus.PRIVATE)
        make_job(make_producer(publish=PublishStatus.SUSPENDED))
        with self.assertNumQueries(4):  # 件数・一覧（判定のサブクエリつき）＋SAVEPOINT・RELEASE
            res = self.client.get(URL)
        items = self.items(res)
        self.assertEqual(res.json()["total"], 7)
        expected = {open_job.id: True, ended.id: False, future.id: False, full.id: False, dates_full.id: False,
                    past_dates.id: False, long_job.id: True}
        self.assertEqual({k: v["isAcceptingApplications"] for k, v in items.items()}, expected)
        self.assertEqual(items[open_job.id]["producer"], {"id": self.producer.id, "businessName": "山田農園",
                                                          "genre": "agriculture"})
        self.assertEqual([i["id"] for i in res.json()["items"]][0], long_job.id)  # 新しい順

    def test_applied_and_screening_do_not_use_slots(self):
        job = make_job(self.producer, slots=1)
        make_job_application(job, status="screening")
        make_job_application(job, status="rejected")
        self.assertTrue(self.client.get(URL).json()["items"][0]["isAcceptingApplications"])

    def test_filters(self):
        tokyo = make_job(self.producer)
        hokkaido = make_job(self.producer, prefecture=Prefecture.objects.create(
            pk=1, area=Area.objects.create(name="北海道", sort_order=1), name="北海道"))
        fishery = make_job(make_producer(business_name="海風水産", genre=Producer.Genre.FISHERY))
        ids = lambda res: [i["id"] for i in res.json()["items"]]  # noqa: E731
        self.assertEqual(ids(self.client.get(URL, {"areaId": hokkaido.prefecture.area_id})), [hokkaido.id])
        self.assertEqual(ids(self.client.get(URL, {"genre": "fishery"})), [fishery.id])
        self.assertEqual(ids(self.client.get(URL, {"prefectureId": 13, "producerId": self.producer.id})), [tokyo.id])
        self.assertEqual(self.client.get(URL, {"genre": "forestry"}).status_code, 400)


class JobDetailTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.job = make_job(requirements=["18歳以上"], slots=3)
        self.today = make_work_date(self.job, days=0, needed_count=2)
        self.full = make_work_date(self.job, days=2, needed_count=1)
        make_work_date(self.job, days=-1)  # 過去は出さない
        make_job_application(self.job, status="hired", work_dates=[self.full])

    def test_detail(self):
        res = self.client.get(f"{URL}/{self.job.id}")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual((data["requirements"], data["applicationQuestions"], data["hasApplied"]),
                         (["18歳以上"], [], False))
        self.assertTrue(data["isAcceptingApplications"])
        self.assertEqual(data["workDates"]["items"], [
            {"id": self.today.id, "workDate": self.today.work_date.isoformat(), "neededCount": 2, "remainingCount": 2,
             "isSelectable": True},
            {"id": self.full.id, "workDate": self.full.work_date.isoformat(), "neededCount": 1, "remainingCount": 0,
             "isSelectable": False},
        ])

    def test_has_applied(self):
        user = make_user(email="worker@example.com")
        make_job_application(self.job, user=user)
        self.signin(user.email)
        self.assertTrue(self.client.get(f"{URL}/{self.job.id}").json()["hasApplied"])

    def test_paging_and_not_found(self):
        res = self.client.get(f"{URL}/{self.job.id}", {"workDatesPageSize": 1, "workDatesPage": 2})
        self.assertEqual([d["id"] for d in res.json()["workDates"]["items"]], [self.full.id])
        ended = make_job(period_end=today_plus(-1))
        self.assertEqual(self.client.get(f"{URL}/{ended.id}").status_code, 200)  # 期間外でも公開中なら見られる
        private = make_job(publish_status=PublishStatus.PRIVATE)
        for job_id in [private.id, 999999, 2 ** 63]:
            res = self.client.get(f"{URL}/{job_id}")
            self.assertEqual((res.status_code, res.json()["errorCode"]), (404, "JOB_NOT_FOUND"))


class ApplyTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.job = make_job(title="にんじん収穫")
        self.date1 = make_work_date(self.job, days=3)
        self.date2 = make_work_date(self.job, days=4)
        self.user = make_user(email="worker@example.com", last_name="佐藤", first_name="花子")
        self.signin(self.user.email)

    def apply(self, job=None, **kw):
        body = {"workDateIds": [self.date2.id, self.date1.id], "message": " よろしくお願いします ",
                "requirementsConfirmed": True}
        body.update(kw)
        with self.captureOnCommitCallbacks(execute=True):
            return self.post_json(f"{URL}/{(job or self.job).id}/applications", body)

    def test_apply(self):
        res = self.apply()
        self.assertEqual(res.status_code, 201, res.json())
        application = JobApplication.objects.get()
        self.assertEqual(res.json(), {
            "id": application.id, "jobId": self.job.id, "workDateIds": [self.date1.id, self.date2.id],
            "message": "よろしくお願いします", "answers": [], "status": "applied", "decidedAt": None,
            "createdAt": res.json()["createdAt"]})
        notice = Notification.objects.get(user=self.job.producer.user)
        self.assertEqual((notice.notification_type, notice.link_path),
                         ("new_application", f"/dashboard/jobs/{self.job.id}/applicants"))
        self.assertFalse(Notification.objects.filter(user=self.user).exists())  # 本人はメールだけ
        self.assertEqual(sorted(m.to[0] for m in mail.outbox), sorted([self.user.email, self.job.producer.user.email]))

    def test_job_without_work_dates(self):
        long_job = make_job(term_type="long")
        self.assertEqual(self.apply(job=long_job, workDateIds=[]).status_code, 201)

    def test_work_date_rules(self):
        res = self.apply(workDateIds=[])
        self.assertEqual((res.status_code, set(res.json()["details"])), (400, {"workDateIds"}))
        other = make_work_date(make_job(), days=3)
        res = self.apply(workDateIds=[other.id])
        self.assertEqual(res.status_code, 400)
        res = self.apply(workDateIds=[self.date1.id, self.date1.id])
        self.assertEqual(res.status_code, 400)
        long_job = make_job(term_type="long")
        self.assertEqual(self.apply(job=long_job, workDateIds=[self.date1.id]).status_code, 400)
        past = make_work_date(self.job, days=-1)
        full = make_work_date(self.job, days=5, needed_count=1)
        make_job_application(self.job, status="hired", work_dates=[full])
        for date in [past, full]:
            res = self.apply(workDateIds=[self.date1.id, date.id])
            self.assertEqual((res.status_code, res.json()["errorCode"]), (409, "WORK_DATE_UNAVAILABLE"))
        self.assertFalse(JobApplication.objects.filter(user=self.user).exists())

    def test_validation(self):
        for body, key in [({"requirementsConfirmed": False}, "requirementsConfirmed"),
                          ({"answers": [{"q": "a"}]}, "answers"), ({"idempotencyKey": "x"}, "idempotencyKey")]:
            res = self.apply(**body)
            self.assertEqual(res.status_code, 400, body)
            self.assertIn(key, res.json()["details"])

    def test_not_accepting(self):
        for job in [make_job(period_end=today_plus(-1)), make_job(period_start=today_plus(1))]:
            make_work_date(job, days=3)
            res = self.apply(job=job, workDateIds=[job.job_work_dates.get().id])
            self.assertEqual((res.status_code, res.json()["errorCode"]), (409, "JOB_NOT_ACCEPTING"))
        full = make_job(term_type="long", slots=1)
        make_job_application(full, status="completed")
        res = self.apply(job=full, workDateIds=[])
        self.assertEqual(res.json()["errorCode"], "JOB_NOT_ACCEPTING")

    def test_already_applied(self):
        self.assertEqual(self.apply().status_code, 201)
        JobApplication.objects.update(status="withdrawn")
        res = self.apply()  # 取り下げのあとも再応募はできない（1人1求人1件）
        self.assertEqual((res.status_code, res.json()["errorCode"]), (409, "ALREADY_APPLIED"))

    def test_own_job_and_not_found(self):
        mine = make_job(make_producer(user=self.user))
        self.assertEqual(self.apply(job=mine, workDateIds=[]).json()["errorCode"], "CANNOT_APPLY_OWN")
        private = make_job(publish_status=PublishStatus.PRIVATE)
        res = self.apply(job=private, workDateIds=[])
        self.assertEqual((res.status_code, res.json()["errorCode"]), (404, "JOB_NOT_FOUND"))

    def test_requires_login(self):
        self.post_json("/api/v1/auth/signout")
        self.assertEqual(self.apply().status_code, 401)


class MyApplicationTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.job = make_job(title="にんじん収穫")
        self.user = make_user(email="worker@example.com")
        self.signin(self.user.email)

    def test_list(self):
        later, earlier = make_work_date(self.job, days=5), make_work_date(self.job, days=-2)
        old = make_job_application(self.job, user=self.user, status="hired", work_dates=[later, earlier])
        JobApplication.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=1))
        private = make_job(title="非公開", publish_status=PublishStatus.PRIVATE)
        new = make_job_application(private, user=self.user)
        make_job_application(self.job)  # 他人の応募
        with self.assertNumQueries(8):  # セッション・ユーザー・公開中の求人・件数・一覧・希望日＋SAVEPOINT・RELEASE
            res = self.client.get(MY_URL)
        items = res.json()["items"]
        self.assertEqual([i["id"] for i in items], [new.id, old.id])
        self.assertEqual(items[0]["job"], {"id": private.id, "title": None, "isPublic": False})
        self.assertEqual(items[1]["job"], {"id": self.job.id, "title": "にんじん収穫", "isPublic": True})
        self.assertEqual([d["id"] for d in items[1]["workDates"]], [earlier.id, later.id])  # 過去の日も含めて日付順
        self.assertEqual((items[0]["withdrawable"], items[1]["withdrawable"]), (True, False))
        self.assertEqual(self.client.get(MY_URL, {"status": "hired"}).json()["total"], 1)

    def test_withdraw(self):
        application = make_job_application(self.job, user=self.user, status="screening")
        with self.captureOnCommitCallbacks(execute=True):
            res = self.post_json(f"{MY_URL}/{application.id}/withdraw")
        self.assertEqual((res.status_code, res.json()["status"], res.json()["withdrawable"]),
                         (200, "withdrawn", False))
        notice = Notification.objects.get(user=self.job.producer.user)
        self.assertEqual(notice.notification_type, "application_withdrawn")
        self.assertEqual(mail.outbox[0].to, [self.job.producer.user.email])
        res = self.post_json(f"{MY_URL}/{application.id}/withdraw")
        self.assertEqual((res.status_code, res.json()["errorCode"]), (409, "WITHDRAW_NOT_ALLOWED"))

    def test_withdraw_not_allowed_after_decision(self):
        application = make_job_application(self.job, user=self.user, status="hired")
        res = self.post_json(f"{MY_URL}/{application.id}/withdraw")
        self.assertEqual(res.json()["errorCode"], "WITHDRAW_NOT_ALLOWED")

    def test_others_application_is_404(self):
        theirs = make_job_application(self.job)
        for application_id in [theirs.id, 999999, 2 ** 63]:
            res = self.post_json(f"{MY_URL}/{application_id}/withdraw")
            self.assertEqual((res.status_code, res.json()["errorCode"]), (404, "APPLICATION_NOT_FOUND"))
        theirs.refresh_from_db()
        self.assertEqual(theirs.status, "applied")
        self.assertEqual(ApplicationWorkDate.objects.count(), 0)
