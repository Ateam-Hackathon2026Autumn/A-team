"""運営ダッシュボード のテスト

テスト対象: api/views/admin/summary.py

確認すること（シーケンス図の opt 分岐ごとに1テストを目安にする）:
  - 運営ダッシュボード: GET /api/v1/admin/summary
      ・新規ユーザー数・申込数・応募数（今日・7日・30日）
      ・未対応件数（審査待ち・問い合わせ open・通報 open・キャンセル申請中・返金待ち）

S3 には接続しない（override_settings で STORAGES を FileSystemStorage にする）
"""
