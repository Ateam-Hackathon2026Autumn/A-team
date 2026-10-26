"""お気に入り（生産者フォローを兼ねる） のシリアライザー

使う view: api/views/public/favorites.py

このファイルに書くもの（リクエストの検証用・レスポンスの形用）:
  - お気に入り一覧（GET /api/v1/users/me/favorites）: クエリ・入力の検証とレスポンス
  - お気に入り登録（商品）（PUT /api/v1/users/me/favorites/products/:productId）: 入力の検証とレスポンス
  - お気に入り解除（商品）（DELETE /api/v1/users/me/favorites/products/:productId）: 入力の検証とレスポンス
  - お気に入り登録（生産者）（PUT /api/v1/users/me/favorites/producers/:producerId）: 入力の検証とレスポンス
  - お気に入り解除（生産者）（DELETE /api/v1/users/me/favorites/producers/:producerId）: 入力の検証とレスポンス

入力エラーは 400（項目ごとのメッセージ）。カラム名は claude/er-diagram.md に合わせる
"""
