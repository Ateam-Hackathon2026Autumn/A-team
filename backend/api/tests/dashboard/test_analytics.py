"""分析 のテスト

テスト対象: api/views/dashboard/analytics.py

確認すること（シーケンス図の opt 分岐ごとに1テストを目安にする）:
  - 分析（生産者）: GET /api/v1/dashboard/analytics
      ・year。月ごとの注文数・売上、商品別販売数上位10、お気に入り数。アクセス数は拡張

S3 には接続しない（override_settings で STORAGES を FileSystemStorage にする）
"""
