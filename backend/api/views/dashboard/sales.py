"""売上

認証: 生産者
共通: 生産者APIの共通チェック（approved でなければ 403、掲載停止中にできない操作は 409）は common/permissions.py

このファイルに書くもの（APIView / generics のクラス）。シーケンス図は Notion の同名の図:
  - 売上: GET /api/v1/dashboard/sales
      ・year・month。発送済み（shipped・delivered）の箱を shipped_at で月ごとに集計。未発送・キャンセル申請中は入金予定
      ・販売手数料は0%

仕様: claude/api-spec.md / カラム名: claude/er-diagram.md
"""
