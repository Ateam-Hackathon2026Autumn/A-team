"""チャット（見た目はチャット、中身はメール型の非同期） のシリアライザー

使う view: api/views/public/chat.py

このファイルに書くもの（リクエストの検証用・レスポンスの形用）:
  - やり取り一覧（GET /api/v1/chat/rooms）: クエリ・入力の検証とレスポンス
  - やり取り開始（POST /api/v1/chat/rooms）: 入力の検証とレスポンス
  - メッセージ一覧（GET /api/v1/chat/rooms/:roomId/messages）: クエリ・入力の検証とレスポンス
  - メッセージ送信（POST /api/v1/chat/rooms/:roomId/messages）: 入力の検証とレスポンス
  - 未読メッセージ数（GET /api/v1/chat/unread-count）: クエリ・入力の検証とレスポンス

入力エラーは 400（項目ごとのメッセージ）。カラム名は claude/er-diagram.md に合わせる
"""
