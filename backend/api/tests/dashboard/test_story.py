"""ストーリー管理（学ぶページ） のテスト

テスト対象: api/views/dashboard/story.py

確認すること（シーケンス図の opt 分岐ごとに1テストを目安にする）:
  - ストーリー取得: GET /api/v1/dashboard/story
      ・行がなければ空の内容を返す
  - ストーリー保存: PUT /api/v1/dashboard/story
      ・各項目2,000文字まで。公開には1項目以上。行がなければ作る。就農理由・目標（reason・goal）もここ

S3 には接続しない（override_settings で STORAGES を FileSystemStorage にする）
"""
