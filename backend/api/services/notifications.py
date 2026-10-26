"""サイト内の通知とメールをまとめて送る

view から呼ぶ業務ロジック。複数のAPI・バッチで同じ処理を使うものをここにまとめる。

書くもの:
  - notifications に1行登録し、同時にメールを送る（ゲストにはメールのみ）
  - notification_type: new_order / shipped / cancel_requested / canceled / application_result / reservation
  - チャットは notifications に入れない。相手がそのやり取りに未読を持っていないときだけメール
  - 止められるメール（メッセージ・お気に入りの新着・お知らせ）だけ notification_settings を見る

使う場所:
  - 注文・発送・キャンセル・予約・応募結果・レビュー返信などの各処理
"""
