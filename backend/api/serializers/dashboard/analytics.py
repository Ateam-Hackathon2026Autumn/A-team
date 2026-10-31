"""分析 のシリアライザー

使う view: api/views/dashboard/analytics.py

このファイルに書くもの（リクエストの検証用・レスポンスの形用）:
  - 分析（生産者）（GET /api/v1/dashboard/analytics）: クエリ・入力の検証とレスポンス

入力エラーは 400（項目ごとのメッセージ）。カラム名は claude/er-diagram.md に合わせる
"""
