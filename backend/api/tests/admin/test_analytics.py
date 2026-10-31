"""分析（運営） のテスト

テスト対象: api/views/admin/analytics.py

確認すること（シーケンス図の opt 分岐ごとに1テストを目安にする）:
  - 分析（管理者）: GET /api/v1/admin/analytics
      ・year。月ごとの売上（発送済みの箱を shipped_at で集計）・新規ユーザー数・注文数・体験予約数・求人応募数、生産者別売上上位20

S3 には接続しない（override_settings で STORAGES を FileSystemStorage にする）
"""
