"""商品管理 のシリアライザー

使う view: api/views/dashboard/products.py

このファイルに書くもの（リクエストの検証用・レスポンスの形用）:
  - 商品一覧（生産者）（GET /api/v1/dashboard/products）: クエリ・入力の検証とレスポンス
  - 商品登録（POST /api/v1/dashboard/products）: 入力の検証とレスポンス
  - 商品詳細（生産者）（GET /api/v1/dashboard/products/:productId）: クエリ・入力の検証とレスポンス
  - 商品更新（PATCH /api/v1/dashboard/products/:productId）: 入力の検証とレスポンス
  - 商品削除（DELETE /api/v1/dashboard/products/:productId）: 入力の検証とレスポンス
  - 在庫更新（PATCH /api/v1/dashboard/products/:productId/stock）: 入力の検証とレスポンス

入力エラーは 400（項目ごとのメッセージ）。カラム名は claude/er-diagram.md に合わせる
"""
