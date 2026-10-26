"""レビュー確認・返信 のシリアライザー

使う view: api/views/dashboard/reviews.py

このファイルに書くもの（リクエストの検証用・レスポンスの形用）:
  - レビュー一覧（生産者）（GET /api/v1/dashboard/reviews）: クエリ・入力の検証とレスポンス
  - レビュー返信（POST /api/v1/dashboard/reviews/:reviewId/reply）: 入力の検証とレスポンス

入力エラーは 400（項目ごとのメッセージ）。カラム名は claude/er-diagram.md に合わせる
"""
