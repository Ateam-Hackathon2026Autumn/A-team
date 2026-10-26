"""会員登録・自分のアカウント のテスト

テスト対象: api/views/public/users.py

確認すること（シーケンス図の opt 分岐ごとに1テストを目安にする）:
  - 新規登録: POST /api/v1/users
      ・last_name・first_name・email・password
      ・登録後ログイン状態にし（セッション再発行）、ゲストのカートを付け替える → services/cart.py
      ・notification_settings を1行作る
  - プロフィール取得: GET /api/v1/users/me
  - プロフィール更新: PATCH /api/v1/users/me
      ・メールアドレスを変えるときは現在のパスワード必須。変更前のアドレスに通知メール
  - 退会: DELETE /api/v1/users/me
      ・現在のパスワード必須
      ・進行中の取引があれば 409 → services/anonymize.py の判定を使う
      ・匿名化（services/anonymize.py）。生産者なら producers.publish_status=suspended。セッションを全削除
  - パスワード変更: PUT /api/v1/users/me/password
      ・現在のパスワード必須。今の端末のセッションは維持し、他の端末のセッションを削除。通知メール

S3 には接続しない（override_settings で STORAGES を FileSystemStorage にする）
"""
