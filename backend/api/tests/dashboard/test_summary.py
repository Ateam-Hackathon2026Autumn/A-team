"""生産者ダッシュボード のテスト

テスト対象: api/views/dashboard/summary.py

確認すること（シーケンス図の opt 分岐ごとに1テストを目安にする）:
  - 生産者ダッシュボード: GET /api/v1/dashboard/summary
      ・公開中の商品・体験・求人数、未発送数（paid の注文の unshipped の箱）、キャンセル申請中の数、今後の予約数、新規応募数（applied）

S3 には接続しない（override_settings で STORAGES を FileSystemStorage にする）
"""
