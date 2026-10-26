"""画像アップロード のシリアライザー

使う view: api/views/public/uploads.py

このファイルに書くもの（リクエストの検証用・レスポンスの形用）:
  - 画像アップロード（POST /api/v1/uploads/images）: 入力の検証とレスポンス

入力エラーは 400（項目ごとのメッセージ）。カラム名は claude/er-diagram.md に合わせる
"""
