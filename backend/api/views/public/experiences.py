"""体験（公開側・申込・自分の申込）

認証: 公開／会員

このファイルに書くもの（APIView / generics のクラス）。シーケンス図は Notion の同名の図:
  - 体験一覧: GET /api/v1/experiences
      ・area_id（prefectures.area_id）・producer_id で絞り込み
      ・次回の開催日（open で締め切り前の最も早い日程）を返す。評価は表示しない
  - 体験詳細: GET /api/v1/experiences/:experienceId
      ・申込できる日程（open かつ start_at − booking_deadline_hours が現在より後）と残り人数・締め切り日時
  - 体験申込: POST /api/v1/experiences/:experienceId/applications
      ・slot_id・大人・子ども・未就学児の人数・代表者氏名・電話・メッセージ・キャンセルポリシー同意
      ・締め切り後・open 以外は 409。同じ日程の重複予約は 409
      ・定員は未就学児を含む全員で判定（reserved_count + 人数 <= capacity のときだけ増やす）
      ・申込時点で status=confirmed（支払いは当日現地）。total_amount を保存。生産者に通知・メール
  - 体験申込状況: GET /api/v1/users/me/experience-applications
      ・確定済みで開催日時がこれからのものだけ。キャンセル可否を返す
  - 体験申込キャンセル: POST /api/v1/users/me/experience-applications/:applicationId/cancel
      ・申込締め切りまで（過ぎたら 409）。canceled にして reserved_count を減らす。生産者に通知・メール

仕様: claude/api-spec.md / カラム名: claude/er-diagram.md
"""
