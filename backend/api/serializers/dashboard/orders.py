"""注文・配送・キャンセル承認（生産者） のシリアライザー

使う view: api/views/dashboard/orders.py

このファイルに書くもの（リクエストの検証用・レスポンスの形用）:
  - 注文一覧（生産者）（GET /api/v1/dashboard/orders）: クエリ・入力の検証とレスポンス
  - 注文詳細（生産者）（GET /api/v1/dashboard/orders/:orderId）: クエリ・入力の検証とレスポンス
  - 発送登録（PATCH /api/v1/dashboard/orders/:orderId/shipping）: 入力の検証とレスポンス
  - キャンセル承認（POST /api/v1/dashboard/orders/:orderId/cancel/approve）: 入力の検証とレスポンス
  - キャンセル拒否（POST /api/v1/dashboard/orders/:orderId/cancel/reject）: 入力の検証とレスポンス

入力エラーは 400（項目ごとのメッセージ）。カラム名は claude/er-diagram.md に合わせる
"""
