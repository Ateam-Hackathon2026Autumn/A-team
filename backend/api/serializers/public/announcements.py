"""運営からのお知らせ（notices テーブル） のシリアライザー

使う view: api/views/public/announcements.py

このファイルに書くもの（リクエストの検証用・レスポンスの形用）:
  - お知らせ一覧（GET /api/v1/announcements）: クエリ・入力の検証とレスポンス
  - お知らせ詳細（GET /api/v1/announcements/:announcementId）: クエリ・入力の検証とレスポンス

入力エラーは 400（項目ごとのメッセージ）。カラム名は claude/er-diagram.md に合わせる
"""
