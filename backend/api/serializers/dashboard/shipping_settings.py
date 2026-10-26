"""配送設定 のシリアライザー

使う view: api/views/dashboard/shipping_settings.py

このファイルに書くもの（リクエストの検証用・レスポンスの形用）:
  - 配送設定取得（GET /api/v1/dashboard/shipping-settings）: クエリ・入力の検証とレスポンス
  - 配送設定保存（PUT /api/v1/dashboard/shipping-settings）: 入力の検証とレスポンス

入力エラーは 400（項目ごとのメッセージ）。カラム名は claude/er-diagram.md に合わせる
"""
