"""分析（運営）

認証: 管理者（権限グループ: 管理者）
共通: 管理者APIの共通チェック（is_staff と権限グループ）は common/permissions.py、データ変更はすべて services/audit.py で audit_logs に記録

このファイルに書くもの（APIView / generics のクラス）。シーケンス図は Notion の同名の図:
  - 分析（管理者）: GET /api/v1/admin/analytics
      ・year。月ごとの売上（発送済みの箱を shipped_at で集計）・新規ユーザー数・注文数・体験予約数・求人応募数、生産者別売上上位20

仕様: claude/api-spec.md / カラム名: claude/er-diagram.md
"""
