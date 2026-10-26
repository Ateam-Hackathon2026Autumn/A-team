"""お知らせ管理（notices テーブル） のテスト

テスト対象: api/views/admin/announcements.py

確認すること（シーケンス図の opt 分岐ごとに1テストを目安にする）:
  - お知らせ一覧（管理者）: GET /api/v1/admin/announcements
      ・状態（下書き＝published_at が空・予約公開＝未来・公開中＝過去）・audience で絞り込み
  - お知らせ作成: POST /api/v1/admin/announcements
      ・title・body・audience・published_at
  - お知らせ更新: PATCH /api/v1/admin/announcements/:announcementId
  - お知らせ削除: DELETE /api/v1/admin/announcements/:announcementId
      ・物理削除

S3 には接続しない（override_settings で STORAGES を FileSystemStorage にする）
"""
