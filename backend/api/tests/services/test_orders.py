"""api/services/orders.py の単体テスト

API を通さずに関数を直接呼び、境界値（0件・上限・端数）を確認する
  - 注文番号（例: TM-20260921-0412）とゲスト用トークン（secrets.token_urlsafe(32)、DBには SHA-256 だけ）を作る
  - orders → order_shipments → order_items の登録、在庫の引き当て（stock >= 数量 のときだけ減らす）をトランザクションで行う
  - キャンセル申請・承認・拒否、在庫の戻し、返金待ちの判定（canceled かつ refunded_amount が空）
  - 状態の更新は「現在の状態が想定どおりのときだけ更新」する条件付き更新にし、更新できなければ 409
"""
