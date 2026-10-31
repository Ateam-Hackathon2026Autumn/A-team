"""サイト内の通知

認証: 会員

このファイルに書くもの（APIView / generics のクラス）。シーケンス図は Notion の同名の図:
  - 通知一覧: GET /api/v1/notifications
      ・自分宛てを新しい順。未読件数も返す
  - 通知を既読にする: PATCH /api/v1/notifications/:notificationId/read
      ・他人の通知は 404

仕様: claude/api-spec.md / カラム名: claude/er-diagram.md
"""
