"""通報対応 のテスト

テスト対象: api/views/admin/reports.py

確認すること（シーケンス図の opt 分岐ごとに1テストを目安にする）:
  - 通報一覧: GET /api/v1/admin/reports
      ・初期値は open を古い順。対象の名前・リンク・公開状態を返す
  - 通報の対応更新: PATCH /api/v1/admin/reports/:reportId
      ・status（resolved・dismissed）と handled_by のみ。掲載停止は contents.py の API で行う

S3 には接続しない（override_settings で STORAGES を FileSystemStorage にする）
"""
