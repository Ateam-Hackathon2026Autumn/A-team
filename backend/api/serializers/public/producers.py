"""生産者・学ぶ（公開側） のシリアライザー

使う view: api/views/public/producers.py

このファイルに書くもの（リクエストの検証用・レスポンスの形用）:
  - 生産者一覧（GET /api/v1/producers）: クエリ・入力の検証とレスポンス
  - 生産者詳細（GET /api/v1/producers/:producerId）: クエリ・入力の検証とレスポンス
  - 生産者ストーリー（学ぶページ）（GET /api/v1/producers/:producerId/story）: クエリ・入力の検証とレスポンス

入力エラーは 400（項目ごとのメッセージ）。カラム名は claude/er-diagram.md に合わせる
"""
