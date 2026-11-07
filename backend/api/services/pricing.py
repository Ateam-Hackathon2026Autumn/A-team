"""金額の計算（すべてサーバー側で計算する）

view から呼ぶ業務ロジック。複数のAPI・バッチで同じ処理を使うものをここにまとめる。

書くもの:
  - カートの商品を箱（生産者×温度帯）に分ける
  - 箱の送料: 箱の商品合計（割引後）が free_shipping_threshold 以上なら0円
  - 消費税額: 税込額×税率÷(100＋税率)、端数切り捨て。送料は10%
  - 返金額: 箱の明細の subtotal の合計＋shipping_fee

使う場所:
  - GET /cart
  - POST /orders
  - キャンセル承認・管理者キャンセル・返金

実装済み:
  - refund_amount(shipment): 返金額（明細の subtotal の合計＋送料）
"""


def refund_amount(shipment):
    """箱1つ分の返金額（円）。明細は shipment.order_items（prefetch 済みならそれ）を使う"""
    return sum(item.subtotal for item in shipment.order_items.all()) + shipment.shipping_fee

