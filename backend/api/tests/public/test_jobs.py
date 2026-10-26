"""求人（公開側・応募・自分の応募） のテスト

テスト対象: api/views/public/jobs.py

確認すること（シーケンス図の opt 分岐ごとに1テストを目安にする）:
  - 求人一覧: GET /api/v1/jobs
      ・area_id・genre（producers.genre）・producer_id。募集期間外は出さない
  - 求人詳細: GET /api/v1/jobs/:jobId
      ・募集期間外は 404。今日以降の勤務日。ログイン中は応募済みかを返す
  - 求人応募: POST /api/v1/jobs/:jobId/applications
      ・message・answers・希望日。勤務日がある求人は希望日1日以上
      ・同じ求人への再応募は不可（409。UNIQUE 制約違反も 409）。応募数の上限なし。年齢はシステムで確認しない
  - 求人応募状況: GET /api/v1/users/me/job-applications
      ・applied・screening・hired だけ。取り下げ可否を返す
  - 求人応募の取り下げ: POST /api/v1/users/me/job-applications/:applicationId/withdraw
      ・applied・screening のときだけ（それ以外は 409）。生産者に通知・メール

S3 には接続しない（override_settings で STORAGES を FileSystemStorage にする）
"""
