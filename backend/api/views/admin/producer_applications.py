"""生産者審査

認証: 管理者（権限グループ: 審査担当・管理者）
共通: 管理者APIの共通チェック（is_staff と権限グループ）は common/permissions.py、データ変更はすべて services/audit.py で audit_logs に記録

このファイルに書くもの（APIView / generics のクラス）。シーケンス図は Notion の同名の図:
  - 生産者申請一覧: GET /api/v1/admin/producer-applications
      ・初期値は pending を申請日の古い順。status で絞り込み
  - 生産者申請詳細: GET /api/v1/admin/producer-applications/:applicationId
      ・書類の期限付きURL、過去の申請履歴
  - 承認: POST /api/v1/admin/producer-applications/:applicationId/approve
      ・書類ごとの check_status を送る。すべて ok のときだけ
      ・producers を approved・approved_at（publish_status は draft のまま）、空の producer_stories を作成、通知・メール
  - 却下: POST /api/v1/admin/producer-applications/:applicationId/reject
      ・review_comment 必須。producers.approval_status=rejected
  - 差し戻し: POST /api/v1/admin/producer-applications/:applicationId/return
      ・review_comment 必須。producers.approval_status=returned

仕様: claude/api-spec.md / カラム名: claude/er-diagram.md
"""
