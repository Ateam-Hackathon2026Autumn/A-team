"""注文・配送・キャンセル承認（生産者）

認証: 生産者
共通: 生産者APIの共通チェック（approved でなければ 403、掲載停止中にできない操作は 409）は common/permissions.py

このファイルに書くもの（APIView / generics のクラス）。シーケンス図は Notion の同名の図:
  - 注文一覧（生産者）: GET /api/v1/dashboard/orders
      ・自分の箱がある paid の注文だけ
  - 注文詳細（生産者）: GET /api/v1/dashboard/orders/:orderId
      ・自分の箱と明細、お届け先（ship_*）だけ。他の生産者の箱と購入者のメールは返さない
  - 発送登録: PATCH /api/v1/dashboard/orders/:orderId/shipping
      ・shipment_id・tracking_no（任意）。unshipped のときだけ shipped にして shipped_at を入れる。購入者に通知・メール
  - キャンセル承認: POST /api/v1/dashboard/orders/:orderId/cancel/approve
      ・自分の箱が cancel_requested のとき。canceled にして在庫を戻す
      ・カードは Stripe で箱ごとに部分返金 → services/payments.py。コンビニ払い・返金エラーは refunded_amount を空のまま（返金待ち）
  - キャンセル拒否: POST /api/v1/dashboard/orders/:orderId/cancel/reject
      ・unshipped に戻す

仕様: claude/api-spec.md / カラム名: claude/er-diagram.md
"""
