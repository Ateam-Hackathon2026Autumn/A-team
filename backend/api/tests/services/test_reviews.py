"""api/services/reviews.py の単体テスト

API を通さずに関数を直接呼び、境界値（0件・上限・端数）を確認する
  - products.rating_avg・review_count を、その商品の product_reviews から AVG・COUNT で集計し直す
  - レビューの登録・編集・削除と同じトランザクションで呼ぶ。0件なら rating_avg を空
"""
