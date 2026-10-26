"""Stripe の Webhook

認証: Stripe（署名で認証）

このファイルに書くもの（APIView / generics のクラス）。シーケンス図は Notion の同名の図:
  - 決済結果の受信（Webhook）: POST /api/v1/webhooks/stripe
      ・署名を検証する（STRIPE_WEBHOOK_SECRET）→ services/payments.py
      ・CSRF の対象外（csrf_exempt）
      ・pending 以外の注文は何もせず 200
      ・succeeded → paid にし、購入者と生産者にメール
      ・payment_failed・canceled（コンビニ払いの期限切れを含む）→ failed にして在庫を戻す

仕様: claude/api-spec.md / カラム名: claude/er-diagram.md
"""
