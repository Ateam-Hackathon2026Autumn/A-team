"""商品・カテゴリー（公開側） のテスト

テスト対象: api/views/public/catalog.py

確認すること（シーケンス図の opt 分岐ごとに1テストを目安にする）:
  - 商品一覧: GET /api/v1/products
      ・公開条件は services/visibility.py
      ・category_id・producer_id で絞り込み
      ・sort: new（created_at）/ price_asc・price_desc（sale_price）/ popular（popularity_score）/ rating（(review_count >= 3) DESC, rating_avg DESC）。どれも最後に id DESC
      ・ページングは common/pagination.py（20件・上限50）
      ・ログイン中はお気に入り済みを返す（Exists のサブクエリ）。在庫0は売り切れ（stock が空なら在庫管理しない）
      ・メイン画像は product_images の sort_order 最小（サブクエリ）。N+1 にしない
  - 商品詳細: GET /api/v1/products/:productId
      ・画像・配送設定・producer_stories.craft・rating_avg・review_count・お気に入り済み
      ・非公開は 404
  - カテゴリー一覧: GET /api/v1/categories
      ・sort_order 順
  - 商品レビュー一覧: GET /api/v1/products/:productId/reviews
      ・新しい順のみ。投稿者名は users.first_name

S3 には接続しない（override_settings で STORAGES を FileSystemStorage にする）
"""
