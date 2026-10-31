"""売上 のテスト

テスト対象: api/views/dashboard/sales.py

確認すること（シーケンス図の opt 分岐ごとに1テストを目安にする）:
  - 売上: GET /api/v1/dashboard/sales
      ・year・month。発送済み（shipped・delivered）の箱を shipped_at で月ごとに集計。未発送・キャンセル申請中は入金予定
      ・販売手数料は0%

S3 には接続しない（override_settings で STORAGES を FileSystemStorage にする）
"""
