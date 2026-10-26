"""管理者ログイン のシリアライザー

使う view: api/views/admin/auth.py

このファイルに書くもの（リクエストの検証用・レスポンスの形用）:
  - 管理者ログインチェック（GET /api/v1/admin/auth/session）: クエリ・入力の検証とレスポンス
  - 管理者ログイン（POST /api/v1/admin/auth/signin）: 入力の検証とレスポンス
  - 管理者ログアウト（POST /api/v1/admin/auth/signout）: 入力の検証とレスポンス

入力エラーは 400（項目ごとのメッセージ）。カラム名は claude/er-diagram.md に合わせる
"""
