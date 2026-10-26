"""生産者ダッシュボード

認証: 生産者
共通: 生産者APIの共通チェック（approved でなければ 403、掲載停止中にできない操作は 409）は common/permissions.py

このファイルに書くもの（APIView / generics のクラス）。シーケンス図は Notion の同名の図:
  - 生産者ダッシュボード: GET /api/v1/dashboard/summary
      ・公開中の商品・体験・求人数、未発送数（paid の注文の unshipped の箱）、キャンセル申請中の数、今後の予約数、新規応募数（applied）

仕様: claude/api-spec.md / カラム名: claude/er-diagram.md
"""
