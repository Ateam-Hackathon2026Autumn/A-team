"""お知らせ管理（notices テーブル）

認証: 管理者（権限グループ: 管理者）
共通: 管理者APIの共通チェック（is_staff と権限グループ）は common/permissions.py、データ変更はすべて services/audit.py で audit_logs に記録

このファイルに書くもの（APIView / generics のクラス）。シーケンス図は Notion の同名の図:
  - お知らせ一覧（管理者）: GET /api/v1/admin/announcements
      ・状態（下書き＝published_at が空・予約公開＝未来・公開中＝過去）・audience で絞り込み
  - お知らせ作成: POST /api/v1/admin/announcements
      ・title・body・audience・published_at
  - お知らせ更新: PATCH /api/v1/admin/announcements/:announcementId
  - お知らせ削除: DELETE /api/v1/admin/announcements/:announcementId
      ・物理削除

仕様: claude/api-spec.md / カラム名: claude/er-diagram.md
"""
