"""サイト内の通知 のテスト

テスト対象: api/views/public/notifications.py

確認すること（シーケンス図の opt 分岐ごとに1テストを目安にする）:
  - 通知一覧: GET /api/v1/notifications
      ・自分宛てを新しい順。未読件数も返す
  - 通知を既読にする: PATCH /api/v1/notifications/:notificationId/read
      ・他人の通知は 404

S3 には接続しない（override_settings で STORAGES を FileSystemStorage にする）
"""
