"""問い合わせ対応

認証: 管理者（権限グループ: CS・管理者）
共通: 管理者APIの共通チェック（is_staff と権限グループ）は common/permissions.py、データ変更はすべて services/audit.py で audit_logs に記録

このファイルに書くもの（APIView / generics のクラス）。シーケンス図は Notion の同名の図:
  - 問い合わせ一覧: GET /api/v1/admin/inquiries
      ・初期値は open・in_progress を優先度の高い順・古い順
  - 問い合わせ詳細: GET /api/v1/admin/inquiries/:inquiryId
      ・対応メモの履歴を含む
  - 問い合わせ更新: PATCH /api/v1/admin/inquiries/:inquiryId
      ・status・priority・assignee_id・note。note があれば inquiry_notes に追加。返信はメールソフトで行う

仕様: claude/api-spec.md / カラム名: claude/er-diagram.md
"""
