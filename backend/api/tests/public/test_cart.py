"""カート のテスト

テスト対象: api/views/public/cart.py

確認すること（シーケンス図の opt 分岐ごとに1テストを目安にする）:
  - カート取得: GET /api/v1/cart
      ・会員は user_id、ゲストは session_key → services/cart.py
      ・購入できない商品（非公開・在庫不足）を判定して返す
      ・箱（生産者×温度帯）ごとに小計・送料 → services/pricing.py
      ・価格は保存しない。表示のたびに最新の sale_price
  - カートに追加: POST /api/v1/cart/items
      ・数量1〜10。同じ商品は加算し、合計10超は 400。在庫不足は 409
      ・CSRF を明示的に確認（ゲストも使う）
  - カートの数量変更: PATCH /api/v1/cart/items/:itemId
      ・他人のカートは 404
  - カートから削除: DELETE /api/v1/cart/items/:itemId
      ・他人のカートは 404

S3 には接続しない（override_settings で STORAGES を FileSystemStorage にする）
"""
