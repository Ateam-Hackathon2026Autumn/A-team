"""通報 のテスト

テスト対象: api/views/public/reports.py

確認すること（シーケンス図の opt 分岐ごとに1テストを目安にする）:
  - 通報: POST /api/v1/reports
      ・target_type（product・experience・job・story・producer・user）
      ・同じ対象を何度でも通報できる
      ・user は生産者がやり取りの相手を通報する場合だけ

S3 には接続しない（override_settings で STORAGES を FileSystemStorage にする）
"""
