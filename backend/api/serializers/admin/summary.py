"""運営ダッシュボード のシリアライザー

使う view: api/views/admin/summary.py

このファイルに書くもの（リクエストの検証用・レスポンスの形用）:
  - 運営ダッシュボード（GET /api/v1/admin/summary）: クエリ・入力の検証とレスポンス

入力エラーは 400（項目ごとのメッセージ）。カラム名は claude/er-diagram.md に合わせる
"""
