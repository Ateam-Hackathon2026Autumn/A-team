"""api/services/cart.py の単体テスト

API を通さずに関数を直接呼び、境界値（0件・上限・端数）を確認する
  - 会員は user_id、ゲストは session_key でカートを引く
  - ログイン・新規登録時に、控えておいたゲストの session_key の行を user_id に付け替える（同じ商品は数量合算、上限10）
"""
