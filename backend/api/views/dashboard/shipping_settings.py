"""配送設定

認証: 生産者
共通: 生産者APIの共通チェック（approved でなければ 403、掲載停止中にできない操作は 409）は common/permissions.py

このファイルに書くもの（APIView / generics のクラス）。シーケンス図は Notion の同名の図:
  - 配送設定取得: GET /api/v1/dashboard/shipping-settings
  - 配送設定保存: PUT /api/v1/dashboard/shipping-settings
      ・温度帯ごとの配列でまとめて保存。商品が使っている温度帯の削除は 409

仕様: claude/api-spec.md / カラム名: claude/er-diagram.md
"""
