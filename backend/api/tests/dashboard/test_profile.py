"""生産者プロフィール のテスト

テスト対象: api/views/dashboard/profile.py

確認すること（シーケンス図の opt 分岐ごとに1テストを目安にする）:
  - 生産者プロフィール取得: GET /api/v1/dashboard/profile
  - 生産者プロフィール更新: PATCH /api/v1/dashboard/profile
      ・business_name・representative_name・genre は変更不可（問い合わせで対応）
      ・publish_status は public・private のみ（掲載停止中は変更不可）
      ・農園画像は配列で置き換え、配列の順を sort_order にする

S3 には接続しない（override_settings で STORAGES を FileSystemStorage にする）
"""
