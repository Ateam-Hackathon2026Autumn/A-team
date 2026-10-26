"""生産者プロフィール のシリアライザー

使う view: api/views/dashboard/profile.py

このファイルに書くもの（リクエストの検証用・レスポンスの形用）:
  - 生産者プロフィール取得（GET /api/v1/dashboard/profile）: クエリ・入力の検証とレスポンス
  - 生産者プロフィール更新（PATCH /api/v1/dashboard/profile）: 入力の検証とレスポンス

入力エラーは 400（項目ごとのメッセージ）。カラム名は claude/er-diagram.md に合わせる
"""
