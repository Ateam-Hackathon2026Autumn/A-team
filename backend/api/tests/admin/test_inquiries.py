"""問い合わせ対応 のテスト

テスト対象: api/views/admin/inquiries.py

確認すること（シーケンス図の opt 分岐ごとに1テストを目安にする）:
  - 問い合わせ一覧: GET /api/v1/admin/inquiries
      ・初期値は open・in_progress を優先度の高い順・古い順
  - 問い合わせ詳細: GET /api/v1/admin/inquiries/:inquiryId
      ・対応メモの履歴を含む
  - 問い合わせ更新: PATCH /api/v1/admin/inquiries/:inquiryId
      ・status・priority・assignee_id・note。note があれば inquiry_notes に追加。返信はメールソフトで行う

S3 には接続しない（override_settings で STORAGES を FileSystemStorage にする）
"""
