"""注目スコア・人気スコアの計算

実行頻度: 毎日深夜（python manage.py update_scores）
シーケンス図: Notion の「注目スコア・人気スコアの計算」（ない場合は api-spec.md「3. 定期実行」）

書くもの（BaseCommand を継承した Command クラス）:
  - producers.featured_score と products.popularity_score を計算して保存する
  - 注目スコアの重み付けはチームで確定させてから実装する
"""
