"""Stripe の Webhook のテスト

テスト対象: api/views/public/webhooks.py

確認すること（シーケンス図の opt 分岐ごとに1テストを目安にする）:
  - 決済結果の受信（Webhook）: POST /api/v1/webhooks/stripe
      ・署名を検証する（STRIPE_WEBHOOK_SECRET）→ services/payments.py
      ・CSRF の対象外（csrf_exempt）
      ・pending 以外の注文は何もせず 200
      ・succeeded → paid にし、購入者と生産者にメール
      ・payment_failed・canceled（コンビニ払いの期限切れを含む）→ failed にして在庫を戻す

S3 には接続しない（override_settings で STORAGES を FileSystemStorage にする）
"""
