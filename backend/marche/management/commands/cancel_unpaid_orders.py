"""未決済注文の自動キャンセル

実行頻度: 5分ごと（python manage.py cancel_unpaid_orders）
シーケンス図: Notion の「未決済注文の自動キャンセル」（ない場合は api-spec.md「3. 定期実行」）

書くもの（BaseCommand を継承した Command クラス）:
  - カード決済で30分以上 pending の注文を対象にする
  - DB より先に Stripe の PaymentIntent をキャンセルする。Stripe で支払い済みなら paid にして残す（スキップ）
  - payment_status=failed（pending のときだけ更新）、在庫を戻す、購入者にメール
  - → services/orders.py・services/payments.py
"""
