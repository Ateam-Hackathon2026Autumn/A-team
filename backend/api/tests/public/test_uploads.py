"""画像アップロード のテスト

テスト対象: api/views/public/uploads.py

確認すること（シーケンス図の opt 分岐ごとに1テストを目安にする）:
  - 画像アップロード: POST /api/v1/uploads/images
      ・jpg・png・サイズ上限。公開用の場所に images/{user_id}/ランダム で保存 → services/storage.py
      ・S3 のキーと表示用URLを返す。DB には書かない
      ・キーを保存する側のAPIで「images/自分のID/ で始まるか」を検証する

S3 には接続しない（override_settings で STORAGES を FileSystemStorage にする）
"""
