"""注文・注文履歴・キャンセル申請（会員・ゲスト） のシリアライザー

使う view: api/views/public/orders.py

このファイルに書くもの（リクエストの検証用・レスポンスの形用）:
  - 注文確定・決済開始（POST /api/v1/orders）: 入力の検証とレスポンス
  - 注文履歴一覧（GET /api/v1/users/me/orders）: クエリ・入力の検証とレスポンス
  - 注文詳細（GET /api/v1/users/me/orders/:orderId）: クエリ・入力の検証とレスポンス
  - キャンセル申請（会員）（POST /api/v1/users/me/orders/:orderId/cancel）: 入力の検証とレスポンス
  - 注文詳細（ゲスト）（GET /api/v1/orders/:orderId）: クエリ・入力の検証とレスポンス
  - キャンセル申請（ゲスト）（POST /api/v1/orders/:orderId/cancel）: 入力の検証とレスポンス

入力エラーは 400（項目ごとのメッセージ）。カラム名は claude/er-diagram.md に合わせる
"""
