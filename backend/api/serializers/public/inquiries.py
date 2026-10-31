"""問い合わせ のシリアライザー

使う view: api/views/public/inquiries.py

このファイルに書くもの（リクエストの検証用・レスポンスの形用）:
  - 問い合わせ送信（POST /api/v1/inquiries）: 入力の検証とレスポンス

入力エラーは 400（項目ごとのメッセージ）。カラム名は claude/er-diagram.md に合わせる
"""
