"""注文・注文履歴・キャンセル申請（会員・ゲスト）

認証: ゲスト可／会員

このファイルに書くもの（APIView / generics のクラス）。シーケンス図は Notion の同名の図:
  - 注文確定・決済開始: POST /api/v1/orders
      ・金額はすべてサーバーで再計算 → services/pricing.py
      ・トランザクション内で orders（payment_status=pending・access_token_hash）→ order_shipments（unshipped）→ order_items を登録し、在庫を減らし（stock >= 数量 のときだけ）、カートを空にする → services/orders.py
      ・その後 Stripe PaymentIntent を作成（コンビニ払いは支払い期限3日）→ services/payments.py
      ・client_secret を返す。ゲストにはトークンも返す
  - 注文履歴一覧: GET /api/v1/users/me/orders
      ・新しい順
  - 注文詳細: GET /api/v1/users/me/orders/:orderId
      ・箱ごとの状態・追跡番号・明細。他人の注文は 404
  - キャンセル申請（会員）: POST /api/v1/users/me/orders/:orderId/cancel
      ・producer_id・cancel_reason
      ・paid かつその生産者の箱がすべて unshipped のときだけ（それ以外は 409）
      ・その生産者の箱をまとめて cancel_requested にし、生産者に通知・メール
  - 注文詳細（ゲスト）: GET /api/v1/orders/:orderId
      ・X-Order-Token ヘッダーのトークンを SHA-256 でハッシュ化して access_token_hash と照合。不一致は 404
      ・Referrer-Policy: no-referrer を付ける
  - キャンセル申請（ゲスト）: POST /api/v1/orders/:orderId/cancel
      ・トークン照合のうえ、会員と同じキャンセル申請

仕様: claude/api-spec.md / カラム名: claude/er-diagram.md
"""
