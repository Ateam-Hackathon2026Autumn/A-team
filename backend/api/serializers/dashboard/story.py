"""ストーリー管理（学ぶページ） のシリアライザー

使う view: api/views/dashboard/story.py

このファイルに書くもの（リクエストの検証用・レスポンスの形用）:
  - ストーリー取得（GET /api/v1/dashboard/story）: クエリ・入力の検証とレスポンス
  - ストーリー保存（PUT /api/v1/dashboard/story）: 入力の検証とレスポンス

入力エラーは 400（項目ごとのメッセージ）。カラム名は claude/er-diagram.md に合わせる
"""
