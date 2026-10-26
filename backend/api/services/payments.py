"""Stripe との連携

view から呼ぶ業務ロジック。複数のAPI・バッチで同じ処理を使うものをここにまとめる。

書くもの:
  - PaymentIntent の作成（card・konbini。コンビニ払いは支払い期限3日）とキャンセル
  - 箱ごとの部分返金（Refund）
  - Webhook の署名検証
  - Stripe のエラーは 502 にする

使う場所:
  - POST /orders
  - POST /webhooks/stripe
  - キャンセル承認
  - 管理者キャンセル・返金
  - 未決済注文の自動キャンセル（バッチ）
"""
