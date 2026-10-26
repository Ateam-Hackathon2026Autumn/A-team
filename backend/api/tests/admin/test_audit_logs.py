"""操作ログ のテスト

テスト対象: api/views/admin/audit_logs.py

確認すること（シーケンス図の opt 分岐ごとに1テストを目安にする）:
  - 操作ログ一覧: GET /api/v1/admin/audit-logs
      ・admin_id・action・target_type・期間で絞り込み

S3 には接続しない（override_settings で STORAGES を FileSystemStorage にする）
"""
