"""チャット（見た目はチャット、中身はメール型の非同期）

認証: 会員

このファイルに書くもの（APIView / generics のクラス）。シーケンス図は Notion の同名の図:
  - やり取り一覧: GET /api/v1/chat/rooms
      ・as=member・producer を指定。last_message_at の降順。最後のメッセージと未読件数
  - やり取り開始: POST /api/v1/chat/rooms
      ・producer_id。始められるのは会員だけ。既存があれば 200 で返す。自分の生産者とは 400
  - メッセージ一覧: GET /api/v1/chat/rooms/:roomId/messages
      ・当事者以外は 404。取得時に相手からの未読を既読にする
      ・添付は期限付きURL（5分）→ services/storage.py。2人の間の注文・予約・応募も返す
  - メッセージ送信: POST /api/v1/chat/rooms/:roomId/messages
      ・multipart（body・画像）。添付は chat/{thread_id}/ランダム に非公開で保存
      ・相手が退会・停止中なら 409。last_message_at を更新
      ・相手にこのやり取りの未読がなければ通知とメール（notification_settings.email_message）
  - 未読メッセージ数: GET /api/v1/chat/unread-count
      ・as=member・producer を指定。チャットのバッジ用

仕様: claude/api-spec.md / カラム名: claude/er-diagram.md
"""
