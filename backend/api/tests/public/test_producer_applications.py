"""生産者申請 のテスト

テスト対象: api/views/public/producer_applications.py

確認すること（シーケンス図の opt 分岐ごとに1テストを目安にする）:
  - 生産者申請: POST /api/v1/producer-applications
      ・multipart（事業者情報・申請理由・書類）。producers がすでにあれば 409
      ・書類は documents/{user_id}/ランダム に非公開で保存 → services/storage.py
      ・producers（approval_status=pending・publish_status=draft）・producer_applications・application_documents をトランザクションで登録。失敗したら保存した書類を削除
  - 申請状況: GET /api/v1/producer-applications/me
      ・最新の申請と review_comment
  - 再申請: PATCH /api/v1/producer-applications/me
      ・差し戻し・却下のどちらでも再申請できる。新しい producer_applications 行を追加。書類は全部出し直し

S3 には接続しない（override_settings で STORAGES を FileSystemStorage にする）
"""
