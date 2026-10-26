"""サイト内の通知 のシリアライザー

使う view: api/views/public/notifications.py

このファイルに書くもの（リクエストの検証用・レスポンスの形用）:
  - 通知一覧（GET /api/v1/notifications）: クエリ・入力の検証とレスポンス
  - 通知を既読にする（PATCH /api/v1/notifications/:notificationId/read）: 入力の検証とレスポンス

入力エラーは 400（項目ごとのメッセージ）。カラム名は claude/er-diagram.md に合わせる
"""
