"""管理者の管理

認証: 管理者（権限グループ: 管理者）
共通: 管理者APIの共通チェック（is_staff と権限グループ）は common/permissions.py、データ変更はすべて services/audit.py で audit_logs に記録

このファイルに書くもの（APIView / generics のクラス）。シーケンス図は Notion の同名の図:
  - 管理者一覧: GET /api/v1/admin/admins
      ・運営スタッフと権限グループ
  - 管理者追加: POST /api/v1/admin/admins
      ・email・氏名・権限グループ。is_staff のアカウントを作成（パスワードは使えない値）し、パスワード設定用のメールを送る
  - 管理者の権限変更: PATCH /api/v1/admin/admins/:adminId
      ・権限グループの置き換え。自分自身・「管理者」グループの最後の1人から外すのは 409
  - 管理者削除: DELETE /api/v1/admin/admins/:adminId
      ・is_active=False・is_staff=False・グループを外す・セッション削除（行は残す）。自分自身・最後の管理者は 409

仕様: claude/api-spec.md / カラム名: claude/er-diagram.md
"""
