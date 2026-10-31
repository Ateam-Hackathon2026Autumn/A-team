"""管理者の管理 のシリアライザー

使う view: api/views/admin/admins.py

このファイルに書くもの（リクエストの検証用・レスポンスの形用）:
  - 管理者一覧（GET /api/v1/admin/admins）: クエリ・入力の検証とレスポンス
  - 管理者追加（POST /api/v1/admin/admins）: 入力の検証とレスポンス
  - 管理者の権限変更（PATCH /api/v1/admin/admins/:adminId）: 入力の検証とレスポンス
  - 管理者削除（DELETE /api/v1/admin/admins/:adminId）: 入力の検証とレスポンス

入力エラーは 400（項目ごとのメッセージ）。カラム名は claude/er-diagram.md に合わせる
"""
