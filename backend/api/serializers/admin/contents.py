"""生産者・商品・体験・求人・ストーリーの管理（掲載停止・再開） のシリアライザー

使う view: api/views/admin/contents.py

このファイルに書くもの（リクエストの検証用・レスポンスの形用）:
  - 一覧（resource = producers・products・experiences・jobs・stories）（GET /api/v1/admin/{resource}）: クエリ・入力の検証とレスポンス
  - 詳細（GET /api/v1/admin/{resource}/:id）: クエリ・入力の検証とレスポンス
  - 掲載停止・再開（PATCH /api/v1/admin/{resource}/:id/status）: 入力の検証とレスポンス

入力エラーは 400（項目ごとのメッセージ）。カラム名は claude/er-diagram.md に合わせる
"""
