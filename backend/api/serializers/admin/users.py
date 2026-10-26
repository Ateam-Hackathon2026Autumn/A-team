"""ユーザー管理 のシリアライザー

使う view: api/views/admin/users.py

このファイルに書くもの（リクエストの検証用・レスポンスの形用）:
  - ユーザー一覧（GET /api/v1/admin/users）: クエリ・入力の検証とレスポンス
  - ユーザー詳細（GET /api/v1/admin/users/:userId）: クエリ・入力の検証とレスポンス
  - 利用停止・再開（PATCH /api/v1/admin/users/:userId/status）: 入力の検証とレスポンス
  - ユーザー削除（DELETE /api/v1/admin/users/:userId）: 入力の検証とレスポンス

入力エラーは 400（項目ごとのメッセージ）。カラム名は claude/er-diagram.md に合わせる
"""
