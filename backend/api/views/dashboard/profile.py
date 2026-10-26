"""生産者プロフィール

認証: 生産者
共通: 生産者APIの共通チェック（approved でなければ 403、掲載停止中にできない操作は 409）は common/permissions.py

このファイルに書くもの（APIView / generics のクラス）。シーケンス図は Notion の同名の図:
  - 生産者プロフィール取得: GET /api/v1/dashboard/profile
  - 生産者プロフィール更新: PATCH /api/v1/dashboard/profile
      ・business_name・representative_name・genre は変更不可（問い合わせで対応）
      ・publish_status は public・private のみ（掲載停止中は変更不可）
      ・農園画像は配列で置き換え、配列の順を sort_order にする

仕様: claude/api-spec.md / カラム名: claude/er-diagram.md
"""
