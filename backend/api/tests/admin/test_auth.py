"""管理者ログイン のテスト

テスト対象: api/views/admin/auth.py

確認すること（シーケンス図の opt 分岐ごとに1テストを目安にする）:
  - 管理者ログインチェック: GET /api/v1/admin/auth/session
      ・CSRF Cookie を発行。is_staff でなければ未ログイン扱い。権限グループを返す
  - 管理者ログイン: POST /api/v1/admin/auth/signin
      ・is_staff でないユーザーも「メールアドレスまたはパスワードが違います」の 401
  - 管理者ログアウト: POST /api/v1/admin/auth/signout

S3 には接続しない（override_settings で STORAGES を FileSystemStorage にする）
"""
