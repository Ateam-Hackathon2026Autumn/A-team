"""レビュー確認・返信 のテスト

テスト対象: api/views/dashboard/reviews.py

確認すること（シーケンス図の opt 分岐ごとに1テストを目安にする）:
  - レビュー一覧（生産者）: GET /api/v1/dashboard/reviews
      ・product_id・未返信だけで絞り込み
  - レビュー返信: POST /api/v1/dashboard/reviews/:reviewId/reply
      ・1,000文字まで。上書き可、空で削除。初めて返信したときだけ投稿者に通知（メールなし）
      ・掲載停止中の生産者は返信不可（409）

S3 には接続しない（override_settings で STORAGES を FileSystemStorage にする）
"""
