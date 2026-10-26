"""分析（運営） のシリアライザー

使う view: api/views/admin/analytics.py

このファイルに書くもの（リクエストの検証用・レスポンスの形用）:
  - 分析（管理者）（GET /api/v1/admin/analytics）: クエリ・入力の検証とレスポンス

入力エラーは 400（項目ごとのメッセージ）。カラム名は claude/er-diagram.md に合わせる
"""
