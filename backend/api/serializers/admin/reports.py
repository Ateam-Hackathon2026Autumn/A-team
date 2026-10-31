"""通報対応 のシリアライザー

使う view: api/views/admin/reports.py

このファイルに書くもの（リクエストの検証用・レスポンスの形用）:
  - 通報一覧（GET /api/v1/admin/reports）: クエリ・入力の検証とレスポンス
  - 通報の対応更新（PATCH /api/v1/admin/reports/:reportId）: 入力の検証とレスポンス

入力エラーは 400（項目ごとのメッセージ）。カラム名は claude/er-diagram.md に合わせる
"""
