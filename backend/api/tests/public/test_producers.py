"""生産者・学ぶ（公開側） のテスト

テスト対象: api/views/public/producers.py

確認すること（シーケンス図の opt 分岐ごとに1テストを目安にする）:
  - 生産者一覧: GET /api/v1/producers
      ・絞り込みは「注目（featured_score 順）」「新規就業（career_start_year が5年以内）」のみ
      ・ログイン中はお気に入り済み。バッジは services/badges.py
  - 生産者詳細: GET /api/v1/producers/:producerId
      ・農園画像・craft・reason・goal（応援ブロック）・バッジ・お気に入り済み
  - 生産者ストーリー（学ぶページ）: GET /api/v1/producers/:producerId/story
      ・producer_stories が public 以外なら 404

S3 には接続しない（override_settings で STORAGES を FileSystemStorage にする）
"""
