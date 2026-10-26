"""お届け先 のテスト

テスト対象: api/views/public/addresses.py

確認すること（シーケンス図の opt 分岐ごとに1テストを目安にする）:
  - お届け先一覧: GET /api/v1/users/me/addresses
      ・デフォルトを先頭
  - お届け先登録: POST /api/v1/users/me/addresses
      ・上限10件（超えたら 409）
      ・デフォルト指定または最初の1件なら、他のデフォルトを解除
  - お届け先更新: PATCH /api/v1/users/me/addresses/:addressId
      ・他人のお届け先は 404
  - お届け先削除: DELETE /api/v1/users/me/addresses/:addressId
      ・デフォルトを消したら、最新のお届け先をデフォルトにする

S3 には接続しない（override_settings で STORAGES を FileSystemStorage にする）
"""
