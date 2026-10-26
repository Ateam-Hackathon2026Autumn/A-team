"""注文・返金管理

認証: 管理者（権限グループ: CS・管理者）
共通: 管理者APIの共通チェック（is_staff と権限グループ）は common/permissions.py、データ変更はすべて services/audit.py で audit_logs に記録

このファイルに書くもの（APIView / generics のクラス）。シーケンス図は Notion の同名の図:
  - 注文一覧（管理者）: GET /api/v1/admin/orders
      ・注文番号・メールのキーワード、payment_status・箱の status・返金待ちだけ・注文日の範囲
  - 注文詳細（管理者）: GET /api/v1/admin/orders/:orderId
      ・購入者の連絡先・決済情報・箱・明細・操作履歴・関係する問い合わせ
  - 注文キャンセル（管理者）: POST /api/v1/admin/orders/:orderId/cancel
      ・shipment_ids・reason。発送済みの箱も可。未発送・キャンセル申請中だった箱は在庫を戻す
      ・カードは自動で部分返金、それ以外は返金待ち。購入者と生産者に通知・メール
  - 返金: POST /api/v1/admin/orders/:orderId/refund
      ・返金待ちの箱（canceled かつ refunded_amount が空）に使う
      ・method: stripe（カードのみ Stripe で再返金）／manual（銀行振込などで返金したことを記録）。返金は箱の全額のみ

仕様: claude/api-spec.md / カラム名: claude/er-diagram.md
"""
