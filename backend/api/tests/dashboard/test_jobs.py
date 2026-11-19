"""求人管理・採用 のテスト

テスト対象: api/views/dashboard/jobs.py

確認すること（シーケンス図の opt 分岐ごとに1テストを目安にする）:
  - 求人一覧（生産者）: GET /api/v1/dashboard/jobs
  - 求人登録: POST /api/v1/dashboard/jobs
      ・勤務日の配列も登録。long は勤務日なし、one_day・short の公開には今日以降の勤務日1日以上。画像は任意
  - 求人詳細（生産者）: GET /api/v1/dashboard/jobs/:jobId
  - 求人更新: PATCH /api/v1/dashboard/jobs/:jobId
      ・勤務日は既存分を id 付きで送り、送られなかったものは削除。希望者がいる勤務日の削除は 409
  - 求人削除: DELETE /api/v1/dashboard/jobs/:jobId
      ・応募されたことがあれば 409（非公開にしてもらう）
  - 求人応募者一覧: GET /api/v1/dashboard/jobs/:jobId/applications
      ・status で絞り込み。氏名・電話・年齢（birth_date から計算）・message・answers・希望日。生年月日とメールは返さない
  - 採用・不採用: PATCH /api/v1/dashboard/jobs/:jobId/applications/:applicationId
      ・applied→screening・hired・rejected、screening→hired・rejected、長期の hired→completed
      ・hired・rejected は戻せない。hired・rejected のときだけ応募者に通知・定型文メール
      ・募集人数を超えても採用可（超えているかを返す）

S3 には接続しない（override_settings で STORAGES を FileSystemStorage にする）
"""
from marche.models import Job, JobApplication, JobWorkDate, PublishStatus

from ..utils import ApiTestCase, make_job, make_job_application, make_producer, make_user, make_work_date

LIST_URL = "/api/v1/dashboard/jobs"


def detail_url(job_id):
    return f"/api/v1/dashboard/jobs/{job_id}"


class SuspendedJobTests(ApiTestCase):
    """運営に掲載停止された求人は、公開状態を変えられない（ステップ14で追加。商品・体験と同じ）"""

    def test_publish_status_is_locked(self):
        producer = make_producer()
        job = make_job(producer, publish_status=PublishStatus.SUSPENDED)
        self.signin(producer.user.email)
        res = self.patch_json(f"/api/v1/dashboard/jobs/{job.id}", {"publishStatus": "public"})
        self.assertEqual((res.status_code, res.json()["errorCode"]), (409, "CONTENT_SUSPENDED"))
        self.assertEqual(Job.objects.get().publish_status, "suspended")
        res = self.patch_json(f"/api/v1/dashboard/jobs/{job.id}", {"title": "直した求人"})
        self.assertEqual(res.status_code, 200, res.json())
        self.assertEqual(Job.objects.get().title, "直した求人")


class JobCountTests(ApiTestCase):
    """応募数・採用数（一覧・詳細）と、勤務日ごとの採用数・残りの人数"""

    def setUp(self):
        super().setUp()
        self.producer = make_producer()
        self.job = make_job(self.producer, slots=3)
        self.day1 = make_work_date(self.job, days=5, needed_count=2)
        self.day2 = make_work_date(self.job, days=6, needed_count=1)
        status = JobApplication.Status
        make_job_application(self.job, status=status.APPLIED, work_dates=[self.day1])
        make_job_application(self.job, status=status.HIRED, work_dates=[self.day1, self.day2])
        make_job_application(self.job, status=status.COMPLETED, work_dates=[self.day2])
        make_job_application(self.job, status=status.REJECTED, work_dates=[self.day1])
        make_job_application(self.job, status=status.WITHDRAWN, work_dates=[self.day1])
        self.signin(self.producer.user.email)

    def test_list_has_counts(self):
        empty = make_job(self.producer, title="応募のない求人")
        make_job_application(make_job(make_producer()))  # 他の生産者の求人の応募は数えない
        items = {item["id"]: item for item in self.client.get(LIST_URL).json()["items"]}
        # 応募数は取り下げを除く4件、採用数は採用＋勤務完了の2件
        self.assertEqual((items[self.job.id]["applicationCount"], items[self.job.id]["hiredCount"]), (4, 2))
        self.assertEqual((items[empty.id]["applicationCount"], items[empty.id]["hiredCount"]), (0, 0))

    def test_list_query_count_does_not_grow(self):
        self.client.get(LIST_URL)
        with self.assertNumQueries(5):  # セッション・ユーザー・生産者・件数・一覧（応募数・採用数はサブクエリ）
            self.client.get(LIST_URL)
        for _ in range(3):
            make_job_application(make_job(self.producer))
        with self.assertNumQueries(5):
            self.client.get(LIST_URL)

    def test_detail_has_counts_per_work_date(self):
        body = self.client.get(detail_url(self.job.id)).json()
        self.assertEqual((body["applicationCount"], body["hiredCount"]), (4, 2))
        self.assertEqual(body["workDates"], [
            {"id": self.day1.id, "workDate": str(self.day1.work_date), "neededCount": 2, "hiredCount": 1,
             "remainingCount": 1},
            # 募集人数より多く採用していても、残りは 0 より小さくしない
            {"id": self.day2.id, "workDate": str(self.day2.work_date), "neededCount": 1, "hiredCount": 2,
             "remainingCount": 0},
        ])

    def test_create_and_update_return_counts(self):
        res = self.patch_json(detail_url(self.job.id), {"title": "名前を変えた求人"})
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual((res.json()["applicationCount"], res.json()["hiredCount"]), (4, 2))
        self.assertEqual(res.json()["workDates"][0]["hiredCount"], 1)


class JobConflictTests(ApiTestCase):
    """409 は共通のエラーの形（errorCode と errorMsg）で返す"""

    def setUp(self):
        super().setUp()
        self.producer = make_producer()
        self.job = make_job(self.producer, publish_status=PublishStatus.PRIVATE)
        self.day = make_work_date(self.job, days=5)
        self.other_day = make_work_date(self.job, days=6)
        self.application = make_job_application(self.job, user=make_user(), work_dates=[self.day])
        self.signin(self.producer.user.email)

    def work_dates(self, *dates):
        return [{"id": d.id, "workDate": str(d.work_date), "neededCount": d.needed_count} for d in dates]

    def test_changing_work_date_with_applicants_is_409(self):
        body = self.work_dates(self.day, self.other_day)
        body[0]["workDate"] = str(self.other_day.work_date.replace(year=self.other_day.work_date.year + 1))
        res = self.patch_json(detail_url(self.job.id), {"workDates": body})
        self.assertEqual(res.status_code, 409, res.content)
        self.assertEqual(res.json(), {"errorCode": "WORK_DATE_HAS_APPLICATIONS",
                                      "errorMsg": "応募者がいる勤務日は変更できません。"})

    def test_deleting_work_date_with_applicants_is_409(self):
        res = self.patch_json(detail_url(self.job.id), {"workDates": self.work_dates(self.other_day)})
        self.assertEqual(res.status_code, 409, res.content)
        self.assertEqual(res.json(), {"errorCode": "WORK_DATE_HAS_APPLICATIONS",
                                      "errorMsg": "応募者が希望している勤務日は削除できません。"})
        self.assertEqual(JobWorkDate.objects.filter(job=self.job).count(), 2)

    def test_deleting_job_with_applications_is_409(self):
        res = self.delete_json(detail_url(self.job.id))
        self.assertEqual(res.status_code, 409, res.content)
        self.assertEqual(res.json(), {"errorCode": "JOB_HAS_APPLICATIONS",
                                      "errorMsg": "応募履歴がある求人は削除できません。非公開にしてください。"})
        self.assertTrue(Job.objects.filter(pk=self.job.pk).exists())

    def test_invalid_status_transition_is_409(self):
        url = f"{detail_url(self.job.id)}/applications/{self.application.id}"
        self.assertEqual(self.patch_json(url, {"status": "rejected"}).status_code, 200)
        res = self.patch_json(url, {"status": "hired"})  # 不採用は戻せない
        self.assertEqual(res.status_code, 409, res.content)
        self.assertEqual(res.json(), {"errorCode": "INVALID_APPLICATION_STATUS_TRANSITION",
                                      "errorMsg": "現在の応募状態から指定された状態には変更できません。"})
