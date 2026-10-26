"""認証（ログイン・ログアウト・パスワード再設定） のシリアライザー

使う view: api/views/public/auth.py

このファイルに書くもの（リクエストの検証用・レスポンスの形用）:
  - ログインチェック（GET /api/v1/auth/session）: クエリ・入力の検証とレスポンス
  - ログイン（POST /api/v1/auth/signin）: 入力の検証とレスポンス
  - ログアウト（POST /api/v1/auth/signout）: 入力の検証とレスポンス
  - パスワード再設定申請（POST /api/v1/auth/password-reset）: 入力の検証とレスポンス
  - パスワード再設定（POST /api/v1/auth/password-reset/confirm）: 入力の検証とレスポンス

入力エラーは 400（項目ごとのメッセージ）。カラム名は claude/er-diagram.md に合わせる
"""
