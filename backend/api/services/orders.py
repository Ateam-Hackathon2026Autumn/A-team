"""注文の作成・状態変更

view から呼ぶ業務ロジック。複数のAPI・バッチで同じ処理を使うものをここにまとめる。

書くもの:
  - 注文番号（例: TM-20260921-0412）とゲスト用トークン（secrets.token_urlsafe(32)、DBには SHA-256 だけ）を作る
  - orders → order_shipments → order_items の登録、在庫の引き当て（stock >= 数量 のときだけ減らす）をトランザクションで行う
  - キャンセル申請・承認・拒否、在庫の戻し、返金待ちの判定（canceled かつ refunded_amount が空）
  - 状態の更新は「現在の状態が想定どおりのときだけ更新」する条件付き更新にし、更新できなければ 409

使う場所:
  - POST /orders
  - キャンセル申請（会員・ゲスト）
  - キャンセル承認・拒否
  - 管理者キャンセル
  - Webhook
  - 未決済注文の自動キャンセル（バッチ）

実装済み:
  - restore_stock(shipment): 箱の明細の数量を在庫に戻す（stock が空＝在庫管理しない商品は何もしない）
  - SHIPMENT_STATE_CONFLICT: 箱の状態が想定と違うときの 409 の errorCode
"""
from django.db.models import F
from django.utils import timezone

from marche.models import Product

# 箱の状態が想定と違う（発送済みをもう一度発送、キャンセル済みをもう一度キャンセル など）
SHIPMENT_STATE_CONFLICT = "SHIPMENT_STATE_CONFLICT"


def restore_stock(shipment):
    """箱の明細の数量を在庫に戻す。呼び出し元のトランザクションの中で使う

    stock が空の商品（在庫管理しない）は戻さない。stock = stock + 数量 を DB 側で計算するので、
    同時に別の注文で在庫が減っても値がずれない。明細は shipment.order_items（prefetch 済みならそれ）を使う。
    """
    now = timezone.now()
    for item in shipment.order_items.all():
        Product.objects.filter(pk=item.product_id, stock__isnull=False).update(
            stock=F("stock") + item.quantity, updated_at=now)
