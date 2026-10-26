"""商品レビューの投稿・編集・削除

認証: 会員

このファイルに書くもの（APIView / generics のクラス）。シーケンス図は Notion の同名の図:
  - レビュー投稿: POST /api/v1/products/:productId/reviews
      ・order_item_id・rating（1〜5）・body
      ・自分の注文で箱が shipped・delivered のときだけ。1明細1件（409）
      ・同じトランザクションで products.rating_avg・review_count を集計し直す → services/reviews.py
      ・生産者に通知
  - レビュー編集: PATCH /api/v1/users/me/reviews/:reviewId
      ・編集後に集計し直す
  - レビュー削除: DELETE /api/v1/users/me/reviews/:reviewId
      ・削除後に集計し直す（0件なら rating_avg を空）

仕様: claude/api-spec.md / カラム名: claude/er-diagram.md
"""
