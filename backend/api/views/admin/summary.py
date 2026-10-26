"""運営ダッシュボード

認証: 管理者（権限グループ: 全グループ）
共通: 管理者APIの共通チェック（is_staff と権限グループ）は common/permissions.py、データ変更はすべて services/audit.py で audit_logs に記録

このファイルに書くもの（APIView / generics のクラス）。シーケンス図は Notion の同名の図:
  - 運営ダッシュボード: GET /api/v1/admin/summary
      ・新規ユーザー数・申込数・応募数（今日・7日・30日）
      ・未対応件数（審査待ち・問い合わせ open・通報 open・キャンセル申請中・返金待ち）

仕様: claude/api-spec.md / カラム名: claude/er-diagram.md
"""
