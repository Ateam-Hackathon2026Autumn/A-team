"""体験管理・予約枠・申込者 のシリアライザー

使う view: api/views/dashboard/experiences.py

このファイルに書くもの（リクエストの検証用・レスポンスの形用）:
  - 体験一覧（生産者）（GET /api/v1/dashboard/experiences）: クエリ・入力の検証とレスポンス
  - 体験登録（POST /api/v1/dashboard/experiences）: 入力の検証とレスポンス
  - 体験詳細（生産者）（GET /api/v1/dashboard/experiences/:experienceId）: クエリ・入力の検証とレスポンス
  - 体験更新（PATCH /api/v1/dashboard/experiences/:experienceId）: 入力の検証とレスポンス
  - 体験削除（DELETE /api/v1/dashboard/experiences/:experienceId）: 入力の検証とレスポンス
  - 体験申込者一覧（GET /api/v1/dashboard/experiences/:experienceId/applications）: クエリ・入力の検証とレスポンス
  - 予約枠一覧（GET /api/v1/dashboard/experiences/:experienceId/slots）: クエリ・入力の検証とレスポンス
  - 予約枠登録（POST /api/v1/dashboard/experiences/:experienceId/slots）: 入力の検証とレスポンス
  - 予約枠更新・中止（PATCH /api/v1/dashboard/experiences/:experienceId/slots/:slotId）: 入力の検証とレスポンス
  - 予約枠削除（DELETE /api/v1/dashboard/experiences/:experienceId/slots/:slotId）: 入力の検証とレスポンス

入力エラーは 400（項目ごとのメッセージ）。カラム名は claude/er-diagram.md に合わせる
"""
