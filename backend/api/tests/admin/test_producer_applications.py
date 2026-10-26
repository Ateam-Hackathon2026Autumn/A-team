"""生産者審査 のテスト

テスト対象: api/views/admin/producer_applications.py

確認すること（シーケンス図の opt 分岐ごとに1テストを目安にする）:
  - 生産者申請一覧: GET /api/v1/admin/producer-applications
      ・初期値は pending を申請日の古い順。status で絞り込み
  - 生産者申請詳細: GET /api/v1/admin/producer-applications/:applicationId
      ・書類の期限付きURL、過去の申請履歴
  - 承認: POST /api/v1/admin/producer-applications/:applicationId/approve
      ・書類ごとの check_status を送る。すべて ok のときだけ
      ・producers を approved・approved_at（publish_status は draft のまま）、空の producer_stories を作成、通知・メール
  - 却下: POST /api/v1/admin/producer-applications/:applicationId/reject
      ・review_comment 必須。producers.approval_status=rejected
  - 差し戻し: POST /api/v1/admin/producer-applications/:applicationId/return
      ・review_comment 必須。producers.approval_status=returned

S3 には接続しない（override_settings で STORAGES を FileSystemStorage にする）
"""
