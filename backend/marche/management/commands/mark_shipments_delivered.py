"""配達完了の自動付与

実行頻度: 毎日深夜（python manage.py mark_shipments_delivered）
シーケンス図: Notion の「配達完了の自動付与」（ない場合は api-spec.md「3. 定期実行」）

書くもの（BaseCommand を継承した Command クラス）:
  - status=shipped で shipped_at が7日以上前の箱を delivered にする
"""
