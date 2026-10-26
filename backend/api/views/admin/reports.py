"""通報対応

認証: 管理者（権限グループ: CS・管理者）
共通: 管理者APIの共通チェック（is_staff と権限グループ）は common/permissions.py、データ変更はすべて services/audit.py で audit_logs に記録

このファイルに書くもの（APIView / generics のクラス）。シーケンス図は Notion の同名の図:
  - 通報一覧: GET /api/v1/admin/reports
      ・初期値は open を古い順。対象の名前・リンク・公開状態を返す
  - 通報の対応更新: PATCH /api/v1/admin/reports/:reportId
      ・status（resolved・dismissed）と handled_by のみ。掲載停止は contents.py の API で行う

仕様: claude/api-spec.md / カラム名: claude/er-diagram.md
"""
