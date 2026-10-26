"""求人管理・採用 のシリアライザー

使う view: api/views/dashboard/jobs.py

このファイルに書くもの（リクエストの検証用・レスポンスの形用）:
  - 求人一覧（生産者）（GET /api/v1/dashboard/jobs）: クエリ・入力の検証とレスポンス
  - 求人登録（POST /api/v1/dashboard/jobs）: 入力の検証とレスポンス
  - 求人詳細（生産者）（GET /api/v1/dashboard/jobs/:jobId）: クエリ・入力の検証とレスポンス
  - 求人更新（PATCH /api/v1/dashboard/jobs/:jobId）: 入力の検証とレスポンス
  - 求人削除（DELETE /api/v1/dashboard/jobs/:jobId）: 入力の検証とレスポンス
  - 求人応募者一覧（GET /api/v1/dashboard/jobs/:jobId/applications）: クエリ・入力の検証とレスポンス
  - 採用・不採用（PATCH /api/v1/dashboard/jobs/:jobId/applications/:applicationId）: 入力の検証とレスポンス

入力エラーは 400（項目ごとのメッセージ）。カラム名は claude/er-diagram.md に合わせる
"""
