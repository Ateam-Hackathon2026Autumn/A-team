"""商品レビューの投稿・編集・削除 のテスト

テスト対象: api/views/public/reviews.py

確認すること（シーケンス図の opt 分岐ごとに1テストを目安にする）:
  - レビュー投稿: POST /api/v1/products/:productId/reviews
      ・order_item_id・rating（1〜5）・body
      ・自分の注文で箱が shipped・delivered のときだけ。1明細1件（409）
      ・同じトランザクションで products.rating_avg・review_count を集計し直す → services/reviews.py
      ・生産者に通知
  - レビュー編集: PATCH /api/v1/users/me/reviews/:reviewId
      ・編集後に集計し直す
  - レビュー削除: DELETE /api/v1/users/me/reviews/:reviewId
      ・削除後に集計し直す（0件なら rating_avg を空）

S3 には接続しない（override_settings で STORAGES を FileSystemStorage にする）
"""
