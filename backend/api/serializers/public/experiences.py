"""体験（公開側・申込・自分の申込） のシリアライザー

使う view: api/views/public/experiences.py

このファイルに書くもの（リクエストの検証用・レスポンスの形用）:
  - 体験一覧（GET /api/v1/experiences）: クエリ・入力の検証とレスポンス
  - 体験詳細（GET /api/v1/experiences/:experienceId）: クエリ・入力の検証とレスポンス
  - 体験申込（POST /api/v1/experiences/:experienceId/applications）: 入力の検証とレスポンス
  - 体験申込状況（GET /api/v1/users/me/experience-applications）: クエリ・入力の検証とレスポンス
  - 体験申込キャンセル（POST /api/v1/users/me/experience-applications/:applicationId/cancel）: 入力の検証とレスポンス

入力エラーは 400（項目ごとのメッセージ）。カラム名は claude/er-diagram.md に合わせる
"""
