"""操作ログ

認証: 管理者（権限グループ: 管理者）
共通: 管理者APIの共通チェック（is_staff と権限グループ）は common/permissions.py、データ変更はすべて services/audit.py で audit_logs に記録

このファイルに書くもの（APIView / generics のクラス）。シーケンス図は Notion の同名の図:
  - 操作ログ一覧: GET /api/v1/admin/audit-logs
      ・admin_id・action・target_type・期間で絞り込み

仕様: claude/api-spec.md / カラム名: claude/er-diagram.md
"""
