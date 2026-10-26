"""生産者・学ぶ（公開側）

認証: 公開

このファイルに書くもの（APIView / generics のクラス）。シーケンス図は Notion の同名の図:
  - 生産者一覧: GET /api/v1/producers
      ・絞り込みは「注目（featured_score 順）」「新規就業（career_start_year が5年以内）」のみ
      ・ログイン中はお気に入り済み。バッジは services/badges.py
  - 生産者詳細: GET /api/v1/producers/:producerId
      ・農園画像・craft・reason・goal（応援ブロック）・バッジ・お気に入り済み
  - 生産者ストーリー（学ぶページ）: GET /api/v1/producers/:producerId/story
      ・producer_stories が public 以外なら 404

仕様: claude/api-spec.md / カラム名: claude/er-diagram.md
"""
