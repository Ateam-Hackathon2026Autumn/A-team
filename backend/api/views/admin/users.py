"""ユーザー管理

認証: 管理者（権限グループ: CS・管理者）
共通: 管理者APIの共通チェック（is_staff と権限グループ）は common/permissions.py、データ変更はすべて services/audit.py で audit_logs に記録

このファイルに書くもの（APIView / generics のクラス）。シーケンス図は Notion の同名の図:
  - ユーザー一覧: GET /api/v1/admin/users
      ・運営スタッフは出さない。キーワード・状態（利用中・停止中・退会済み）・生産者かどうか
  - ユーザー詳細: GET /api/v1/admin/users/:userId
      ・取引件数・進行中の取引・通報・操作履歴
  - 利用停止・再開: PATCH /api/v1/admin/users/:userId/status
      ・action（stop・resume）。stop は reason 必須、is_active=False、生産者なら suspended、セッション削除、本人にメール
      ・resume は生産者の状態を戻さない
  - ユーザー削除: DELETE /api/v1/admin/users/:userId
      ・reason 必須。匿名化 → services/anonymize.py。運営スタッフは不可

仕様: claude/api-spec.md / カラム名: claude/er-diagram.md
"""
