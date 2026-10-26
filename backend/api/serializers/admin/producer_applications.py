"""生産者審査 のシリアライザー

使う view: api/views/admin/producer_applications.py

このファイルに書くもの（リクエストの検証用・レスポンスの形用）:
  - 生産者申請一覧（GET /api/v1/admin/producer-applications）: クエリ・入力の検証とレスポンス
  - 生産者申請詳細（GET /api/v1/admin/producer-applications/:applicationId）: クエリ・入力の検証とレスポンス
  - 承認（POST /api/v1/admin/producer-applications/:applicationId/approve）: 入力の検証とレスポンス
  - 却下（POST /api/v1/admin/producer-applications/:applicationId/reject）: 入力の検証とレスポンス
  - 差し戻し（POST /api/v1/admin/producer-applications/:applicationId/return）: 入力の検証とレスポンス

入力エラーは 400（項目ごとのメッセージ）。カラム名は claude/er-diagram.md に合わせる
"""
