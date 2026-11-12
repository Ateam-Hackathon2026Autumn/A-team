"""api/services/pricing.py の単体テスト

API を通さずに関数を直接呼び、境界値（0件・上限・端数）を確認する
  - 消費税額 tax_amounts: 税率ごとに税込合計を出してから 税込額×税率÷(100＋税率)、端数切り捨て。送料は10%
  （箱分け・送料はカートのテスト、返金額は注文管理のテストで確認している）
"""
from django.test import SimpleTestCase

from ...services.pricing import tax_amounts


class TaxAmountTests(SimpleTestCase):
    def test_no_lines(self):
        self.assertEqual(tax_amounts([], 0), (0, 0))

    def test_rounds_down_after_summing(self):
        # 1行ずつ切り捨てる（7＋7＝14）のではなく、合計 216円 から1回だけ計算する（16）
        self.assertEqual(tax_amounts([(8, 108), (8, 108)], 0)[0], 16)
        self.assertEqual(tax_amounts([(8, 107)], 0), (7, 0))

    def test_shipping_is_ten_percent(self):
        self.assertEqual(tax_amounts([(8, 1080)], 1100), (80, 100))
        self.assertEqual(tax_amounts([(10, 1100)], 1100), (0, 200))
