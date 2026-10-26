"""商品管理

認証: 生産者
共通: 生産者APIの共通チェック（approved でなければ 403、掲載停止中にできない操作は 409）は common/permissions.py

このファイルに書くもの（APIView / generics のクラス）。シーケンス図は Notion の同名の図:
  - 商品一覧（生産者）: GET /api/v1/dashboard/products
  - 商品登録: POST /api/v1/dashboard/products
      ・price >= 1、tax_rate は 8 か 10、discount_rate は 1〜99 または空
      ・公開には画像1枚以上。配送設定は自分のもの。画像キーは images/自分のID/ で始まるか検証
  - 商品詳細（生産者）: GET /api/v1/dashboard/products/:productId
      ・他人の商品は 404
  - 商品更新: PATCH /api/v1/dashboard/products/:productId
      ・stock は受け付けない（在庫更新APIだけ）
      ・運営に掲載停止された商品は内容の編集は可、publish_status の変更は 409
  - 商品削除: DELETE /api/v1/dashboard/products/:productId
      ・注文されたことがあれば 409（非公開にしてもらう）
  - 在庫更新: PATCH /api/v1/dashboard/products/:productId/stock
      ・0以上または空（在庫管理しない）

仕様: claude/api-spec.md / カラム名: claude/er-diagram.md
"""
