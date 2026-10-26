"""退会・管理者のユーザー削除

view から呼ぶ業務ロジック。複数のAPI・バッチで同じ処理を使うものをここにまとめる。

書くもの:
  - 進行中の取引の判定（購入者として／生産者として）。あれば 409
  - 匿名化の前に本人へメール → email を deleted_{id}@invalid、氏名を「退会ユーザー」、phone・birth_date・profile_image を空、パスワードを使えない値、is_active=False、deleted_at=現在
  - addresses・cart_items・favorite_products・favorite_producers を削除。注文・予約・応募・レビュー・メッセージは残す
  - 生産者なら producers.publish_status=suspended

使う場所:
  - DELETE /users/me
  - DELETE /admin/users/:userId
"""
