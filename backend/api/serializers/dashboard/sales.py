"""売上 のシリアライザー

使う view: api/views/dashboard/sales.py

このファイルに書くもの（リクエストの検証用・レスポンスの形用）:
  - 売上（GET /api/v1/dashboard/sales）: クエリ・入力の検証とレスポンス

入力エラーは 400（項目ごとのメッセージ）。カラム名は claude/er-diagram.md に合わせる
"""
