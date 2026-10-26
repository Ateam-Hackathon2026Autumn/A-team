"""商品の評価の集計

view から呼ぶ業務ロジック。複数のAPI・バッチで同じ処理を使うものをここにまとめる。

書くもの:
  - products.rating_avg・review_count を、その商品の product_reviews から AVG・COUNT で集計し直す
  - レビューの登録・編集・削除と同じトランザクションで呼ぶ。0件なら rating_avg を空

使う場所:
  - POST /products/:productId/reviews
  - PATCH・DELETE /users/me/reviews/:reviewId
"""
