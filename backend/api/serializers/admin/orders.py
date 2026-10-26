"""注文・返金管理 のシリアライザー

使う view: api/views/admin/orders.py

このファイルに書くもの（リクエストの検証用・レスポンスの形用）:
  - 注文一覧（管理者）（GET /api/v1/admin/orders）: クエリ・入力の検証とレスポンス
  - 注文詳細（管理者）（GET /api/v1/admin/orders/:orderId）: クエリ・入力の検証とレスポンス
  - 注文キャンセル（管理者）（POST /api/v1/admin/orders/:orderId/cancel）: 入力の検証とレスポンス
  - 返金（POST /api/v1/admin/orders/:orderId/refund）: 入力の検証とレスポンス

入力エラーは 400（項目ごとのメッセージ）。カラム名は claude/er-diagram.md に合わせる
"""
