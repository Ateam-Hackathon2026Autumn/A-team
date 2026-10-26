"""運営からのお知らせ（notices テーブル） のテスト

テスト対象: api/views/public/announcements.py

確認すること（シーケンス図の opt 分岐ごとに1テストを目安にする）:
  - お知らせ一覧: GET /api/v1/announcements
      ・audience が all・consumer で published_at が現在以前
      ・audience=producer は生産者ログイン必須で all・producer を返す
  - お知らせ詳細: GET /api/v1/announcements/:announcementId
      ・未公開は 404。producer 向けは生産者以外には 404

S3 には接続しない（override_settings で STORAGES を FileSystemStorage にする）
"""
