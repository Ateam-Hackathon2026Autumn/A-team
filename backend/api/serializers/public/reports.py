"""通報 のシリアライザー

使う view: api/views/public/reports.py

このファイルに書くもの（リクエストの検証用・レスポンスの形用）:
  - 通報（POST /api/v1/reports）: 入力の検証とレスポンス

入力エラーは 400（項目ごとのメッセージ）。カラム名は claude/er-diagram.md に合わせる
"""
