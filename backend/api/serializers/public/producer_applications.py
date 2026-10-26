"""生産者申請 のシリアライザー

使う view: api/views/public/producer_applications.py

このファイルに書くもの（リクエストの検証用・レスポンスの形用）:
  - 生産者申請（POST /api/v1/producer-applications）: 入力の検証とレスポンス
  - 申請状況（GET /api/v1/producer-applications/me）: クエリ・入力の検証とレスポンス
  - 再申請（PATCH /api/v1/producer-applications/me）: 入力の検証とレスポンス

入力エラーは 400（項目ごとのメッセージ）。カラム名は claude/er-diagram.md に合わせる
"""
