"""お届け先 のシリアライザー

使う view: api/views/public/addresses.py

このファイルに書くもの（リクエストの検証用・レスポンスの形用）:
  - お届け先一覧（GET /api/v1/users/me/addresses）: クエリ・入力の検証とレスポンス
  - お届け先登録（POST /api/v1/users/me/addresses）: 入力の検証とレスポンス
  - お届け先更新（PATCH /api/v1/users/me/addresses/:addressId）: 入力の検証とレスポンス
  - お届け先削除（DELETE /api/v1/users/me/addresses/:addressId）: 入力の検証とレスポンス

入力エラーは 400（項目ごとのメッセージ）。カラム名は claude/er-diagram.md に合わせる
"""
