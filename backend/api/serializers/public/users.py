"""会員登録・自分のアカウント のシリアライザー

使う view: api/views/public/users.py

このファイルに書くもの（リクエストの検証用・レスポンスの形用）:
  - 新規登録（POST /api/v1/users）: 入力の検証とレスポンス
  - プロフィール取得（GET /api/v1/users/me）: クエリ・入力の検証とレスポンス
  - プロフィール更新（PATCH /api/v1/users/me）: 入力の検証とレスポンス
  - 退会（DELETE /api/v1/users/me）: 入力の検証とレスポンス
  - パスワード変更（PUT /api/v1/users/me/password）: 入力の検証とレスポンス

入力エラーは 400（項目ごとのメッセージ）。カラム名は claude/er-diagram.md に合わせる
"""
