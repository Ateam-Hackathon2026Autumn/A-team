"""公開側に表示してよいかの条件（QuerySet）

view から呼ぶ業務ロジック。複数のAPI・バッチで同じ処理を使うものをここにまとめる。

書くもの:
  - 生産者: approval_status=approved かつ publish_status=public
  - 商品・体験・求人・ストーリー: 自身の publish_status=public かつ生産者が上の条件を満たす
  - 生産者を掲載停止すると、商品などの状態は変えなくても公開側から消える

使う場所:
  - GET /products 系
  - GET /producers 系
  - GET /experiences 系
  - GET /jobs 系
  - お気に入り登録
  - カート・注文の購入可否
"""
