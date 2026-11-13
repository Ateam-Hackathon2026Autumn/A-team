"""配送設定 のテスト

テスト対象: api/views/dashboard/shipping_settings.py

確認すること（シーケンス図の opt 分岐ごとに1テストを目安にする）:
  - 配送設定取得: GET /api/v1/dashboard/shipping-settings
  - 配送設定保存: PUT /api/v1/dashboard/shipping-settings
      ・温度帯ごとの配列でまとめて保存。商品が使っている温度帯の削除は 409

S3 には接続しない（override_settings で STORAGES を FileSystemStorage にする）
"""
