"""運営からのお知らせ（notices テーブル）

認証: 公開

このファイルに書くもの（APIView / generics のクラス）。シーケンス図は Notion の同名の図:
  - お知らせ一覧: GET /api/v1/announcements
      ・audience が all・consumer で published_at が現在以前
      ・audience=producer は生産者ログイン必須で all・producer を返す
  - お知らせ詳細: GET /api/v1/announcements/:announcementId
      ・未公開は 404。producer 向けは生産者以外には 404

仕様: claude/api-spec.md / カラム名: claude/er-diagram.md
"""
