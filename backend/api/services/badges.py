"""生産者のバッジ判定（列では持たない）

view から呼ぶ業務ロジック。複数のAPI・バッチで同じ処理を使うものをここにまとめる。

書くもの:
  - 新規就業: career_start_year が5年以内（genre で「新規就農」「新規就漁」などに出し分け）
  - 新規参加: approved_at から30日以内
  - 体験受け入れ中: accepts_experience / 担い手募集中: recruiting

使う場所:
  - GET /producers
  - GET /producers/:producerId
"""
