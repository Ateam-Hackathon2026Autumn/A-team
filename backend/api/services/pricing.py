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
  - shipping_fee_for(setting, items_total): 箱の送料（送料無料の条件を満たせば0円）
  - group_into_boxes(lines): 明細を箱（生産者×温度帯）に分け、箱ごとの小計・送料を出す
  - refund_amount(shipment): 返金額（明細の subtotal の合計＋送料）
"""


def refund_amount(shipment):
    """箱1つ分の返金額（円）。明細は shipment.order_items（prefetch 済みならそれ）を使う"""
    return sum(item.subtotal for item in shipment.order_items.all()) + shipment.shipping_fee



def shipping_fee_for(setting, items_total):
    """箱の送料（円）。箱の商品合計（割引後）が free_shipping_threshold 以上なら0円（空なら送料無料にしない）"""
    if setting.free_shipping_threshold is not None and items_total >= setting.free_shipping_threshold:
        return 0
    return setting.shipping_fee


def group_into_boxes(lines):
    """明細を箱に分ける。lines は (product, subtotal, line_id) の並び（product は producer・shipping_setting を JOIN 済み）

    返り値は箱の並び（最初に出てきた順）。1箱は
    {"producer", "setting", "line_ids", "items_total", "shipping_fee"}
    同じ生産者でも温度帯（配送設定）が違えば別の箱。送料は箱ごとにかかる。
    """
    boxes = {}
    for product, subtotal, line_id in lines:
        key = (product.producer_id, product.shipping_setting_id)
        box = boxes.setdefault(key, {"producer": product.producer, "setting": product.shipping_setting,
                                     "line_ids": [], "items_total": 0})
        box["line_ids"].append(line_id)
        box["items_total"] += subtotal
    for box in boxes.values():
        box["shipping_fee"] = shipping_fee_for(box["setting"], box["items_total"])
    return list(boxes.values())
