"""カートの持ち主の判定と付け替え

view から呼ぶ業務ロジック。複数のAPI・バッチで同じ処理を使うものをここにまとめる。

書くもの:
  - 会員は user_id、ゲストは session_key でカートを引く
  - ログイン・新規登録時に、控えておいたゲストの session_key の行を user_id に付け替える（同じ商品は数量合算、上限10）

使う場所:
  - GET・POST・PATCH・DELETE /cart
  - POST /auth/signin
  - POST /users
  - POST /orders（カートを空にする）
"""
