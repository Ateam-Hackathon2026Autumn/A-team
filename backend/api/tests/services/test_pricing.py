"""api/services/pricing.py の単体テスト

API を通さずに関数を直接呼び、境界値（0件・上限・端数）を確認する
  - カートの商品を箱（生産者×温度帯）に分ける
  - 箱の送料: 箱の商品合計（割引後）が free_shipping_threshold 以上なら0円
  - 消費税額: 税込額×税率÷(100＋税率)、端数切り捨て。送料は10%
  - 返金額: 箱の明細の subtotal の合計＋shipping_fee
"""
