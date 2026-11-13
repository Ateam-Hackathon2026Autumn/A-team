"""勤務完了の自動付与

実行頻度: 毎日深夜（python manage.py complete_job_applications）
シーケンス図: Notion の「勤務完了の自動付与」（ない場合は api-spec.md「3. 定期実行」）

書くもの（BaseCommand を継承した Command クラス）:
  - one_day・short の求人で、hired の応募の希望日がすべて過ぎたら completed にする
  - long は生産者が手動（PATCH /dashboard/jobs/:jobId/applications/:applicationId）
"""
