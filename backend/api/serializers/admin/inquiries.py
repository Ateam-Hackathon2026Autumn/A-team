"""問い合わせ対応 のシリアライザー

使う view: api/views/admin/inquiries.py

このファイルに書くもの（リクエストの検証用・レスポンスの形用）:
  - 問い合わせ一覧（GET /api/v1/admin/inquiries）: クエリ・入力の検証とレスポンス
  - 問い合わせ詳細（GET /api/v1/admin/inquiries/:inquiryId）: クエリ・入力の検証とレスポンス
  - 問い合わせ更新（PATCH /api/v1/admin/inquiries/:inquiryId）: 入力の検証とレスポンス

入力エラーは 400（項目ごとのメッセージ）。カラム名は claude/er-diagram.md に合わせる
"""
