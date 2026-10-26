"""体験管理・予約枠・申込者 のテスト

テスト対象: api/views/dashboard/experiences.py

確認すること（シーケンス図の opt 分岐ごとに1テストを目安にする）:
  - 体験一覧（生産者）: GET /api/v1/dashboard/experiences
  - 体験登録: POST /api/v1/dashboard/experiences
      ・booking_deadline_hours は 0〜168。prefecture_id 省略時は生産者の都道府県。公開には画像1枚以上
  - 体験詳細（生産者）: GET /api/v1/dashboard/experiences/:experienceId
  - 体験更新: PATCH /api/v1/dashboard/experiences/:experienceId
      ・料金を変えても既存予約の total_amount は変えない
  - 体験削除: DELETE /api/v1/dashboard/experiences/:experienceId
      ・予約されたことがあれば 409（非公開にしてもらう）
  - 体験申込者一覧: GET /api/v1/dashboard/experiences/:experienceId/applications
      ・slot_id で絞り込み。代表者氏名・電話・人数・メッセージ（メールは返さない）
  - 予約枠一覧: GET /api/v1/dashboard/experiences/:experienceId/slots
  - 予約枠登録: POST /api/v1/dashboard/experiences/:experienceId/slots
      ・1件ずつ。start_at は未来
  - 予約枠更新・中止: PATCH /api/v1/dashboard/experiences/:experienceId/slots/:slotId
      ・過去・中止済みは 409。予約があれば start_at・duration_min は変更不可、capacity は reserved_count 以上
      ・status は open・closed・canceled。canceled（中止）にすると確定済み予約を全キャンセルし予約者に通知・メール（元に戻せない。掲載停止中でも可）
  - 予約枠削除: DELETE /api/v1/dashboard/experiences/:experienceId/slots/:slotId
      ・予約されたことがあれば 409（中止にしてもらう）。過去は 409

S3 には接続しない（override_settings で STORAGES を FileSystemStorage にする）
"""
