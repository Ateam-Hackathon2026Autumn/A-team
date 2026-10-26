"""操作ログ のシリアライザー

使う view: api/views/admin/audit_logs.py

このファイルに書くもの（リクエストの検証用・レスポンスの形用）:
  - 操作ログ一覧（GET /api/v1/admin/audit-logs）: クエリ・入力の検証とレスポンス

入力エラーは 400（項目ごとのメッセージ）。カラム名は claude/er-diagram.md に合わせる
"""
