"""求人（公開側・応募・自分の応募） のシリアライザー

使う view: api/views/public/jobs.py

このファイルに書くもの（リクエストの検証用・レスポンスの形用）:
  - 求人一覧（GET /api/v1/jobs）: クエリ・入力の検証とレスポンス
  - 求人詳細（GET /api/v1/jobs/:jobId）: クエリ・入力の検証とレスポンス
  - 求人応募（POST /api/v1/jobs/:jobId/applications）: 入力の検証とレスポンス
  - 求人応募状況（GET /api/v1/users/me/job-applications）: クエリ・入力の検証とレスポンス
  - 求人応募の取り下げ（POST /api/v1/users/me/job-applications/:applicationId/withdraw）: 入力の検証とレスポンス

入力エラーは 400（項目ごとのメッセージ）。カラム名は claude/er-diagram.md に合わせる
"""
