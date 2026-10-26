"""お気に入り（生産者フォローを兼ねる） のテスト

テスト対象: api/views/public/favorites.py

確認すること（シーケンス図の opt 分岐ごとに1テストを目安にする）:
  - お気に入り一覧: GET /api/v1/users/me/favorites
      ・type=product・producer を指定。非公開になったものも残し、公開中かを返す
  - お気に入り登録（商品）: PUT /api/v1/users/me/favorites/products/:productId
      ・公開中のみ登録可。登録済みでもエラーにしない
  - お気に入り解除（商品）: DELETE /api/v1/users/me/favorites/products/:productId
      ・未登録でもエラーにしない
  - お気に入り登録（生産者）: PUT /api/v1/users/me/favorites/producers/:producerId
      ・notify（省略時 False）も受け取る。登録済みなら notify を更新
  - お気に入り解除（生産者）: DELETE /api/v1/users/me/favorites/producers/:producerId

S3 には接続しない（override_settings で STORAGES を FileSystemStorage にする）
"""
