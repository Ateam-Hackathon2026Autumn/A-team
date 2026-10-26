"""体験の参加済みの自動付与

実行頻度: 毎日深夜（python manage.py mark_reservations_attended）
シーケンス図: Notion の「体験の参加済みの自動付与」（ない場合は api-spec.md「3. 定期実行」）

書くもの（BaseCommand を継承した Command クラス）:
  - status=confirmed で start_at＋duration_min を過ぎた予約を attended にする
"""
