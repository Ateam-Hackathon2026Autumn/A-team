"""お知らせ管理（notices テーブル） のシリアライザー

使う view: api/views/admin/announcements.py

このファイルに書くもの（リクエストの検証用・レスポンスの形用）:
  - お知らせ一覧（管理者）（GET /api/v1/admin/announcements）: クエリ・入力の検証とレスポンス
  - お知らせ作成（POST /api/v1/admin/announcements）: 入力の検証とレスポンス
  - お知らせ更新（PATCH /api/v1/admin/announcements/:announcementId）: 入力の検証とレスポンス
  - お知らせ削除（DELETE /api/v1/admin/announcements/:announcementId）: 入力の検証とレスポンス

入力エラーは 400（項目ごとのメッセージ）。カラム名は claude/er-diagram.md に合わせる
"""
