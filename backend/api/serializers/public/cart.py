"""カート のシリアライザー

使う view: api/views/public/cart.py

このファイルに書くもの（リクエストの検証用・レスポンスの形用）:
  - カート取得（GET /api/v1/cart）: クエリ・入力の検証とレスポンス
  - カートに追加（POST /api/v1/cart/items）: 入力の検証とレスポンス
  - カートの数量変更（PATCH /api/v1/cart/items/:itemId）: 入力の検証とレスポンス
  - カートから削除（DELETE /api/v1/cart/items/:itemId）: 入力の検証とレスポンス

入力エラーは 400（項目ごとのメッセージ）。カラム名は claude/er-diagram.md に合わせる
"""
