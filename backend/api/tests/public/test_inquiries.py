"""問い合わせ のテスト

テスト対象: api/views/public/inquiries.py

確認すること（シーケンス図の opt 分岐ごとに1テストを目安にする）:
  - 問い合わせ送信: POST /api/v1/inquiries
      ・同じIPから1時間5回まで（429）→ common/throttles.py
      ・order_id はログイン中の会員の自分の注文だけ
      ・受付メールを自動送信。CSRF を明示的に確認

S3 には接続しない（override_settings で STORAGES を FileSystemStorage にする）
"""
