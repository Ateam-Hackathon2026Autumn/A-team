"""管理者の管理 のテスト

テスト対象: api/views/admin/admins.py

確認すること（シーケンス図の opt 分岐ごとに1テストを目安にする）:
  - 管理者一覧: GET /api/v1/admin/admins
      ・運営スタッフと権限グループ
  - 管理者追加: POST /api/v1/admin/admins
      ・email・氏名・権限グループ。is_staff のアカウントを作成（パスワードは使えない値）し、パスワード設定用のメールを送る
  - 管理者の権限変更: PATCH /api/v1/admin/admins/:adminId
      ・権限グループの置き換え。自分自身・「管理者」グループの最後の1人から外すのは 409
  - 管理者削除: DELETE /api/v1/admin/admins/:adminId
      ・is_active=False・is_staff=False・グループを外す・セッション削除（行は残す）。自分自身・最後の管理者は 409

S3 には接続しない（override_settings で STORAGES を FileSystemStorage にする）
"""
