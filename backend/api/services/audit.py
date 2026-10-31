"""管理者の操作ログ

view から呼ぶ業務ロジック。複数のAPI・バッチで同じ処理を使うものをここにまとめる。

書くもの:
  - audit_logs に action・target_type・target_id・detail（理由や変更前後の値）を記録する

使う場所:
  - 管理者APIのデータを変える操作すべて
"""
