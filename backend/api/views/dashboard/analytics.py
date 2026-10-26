"""分析

認証: 生産者
共通: 生産者APIの共通チェック（approved でなければ 403、掲載停止中にできない操作は 409）は common/permissions.py

このファイルに書くもの（APIView / generics のクラス）。シーケンス図は Notion の同名の図:
  - 分析（生産者）: GET /api/v1/dashboard/analytics
      ・year。月ごとの注文数・売上、商品別販売数上位10、お気に入り数。アクセス数は拡張

仕様: claude/api-spec.md / カラム名: claude/er-diagram.md
"""
