"""商品・カテゴリー（公開側） のシリアライザー

使う view: api/views/public/catalog.py

このファイルに書くもの（リクエストの検証用・レスポンスの形用）:
  - 商品一覧（GET /api/v1/products）: クエリ・入力の検証とレスポンス
  - 商品詳細（GET /api/v1/products/:productId）: クエリ・入力の検証とレスポンス
  - カテゴリー一覧（GET /api/v1/categories）: クエリ・入力の検証とレスポンス
  - 商品レビュー一覧（GET /api/v1/products/:productId/reviews）: クエリ・入力の検証とレスポンス

入力エラーは 400（項目ごとのメッセージ）。カラム名は claude/er-diagram.md に合わせる
"""
