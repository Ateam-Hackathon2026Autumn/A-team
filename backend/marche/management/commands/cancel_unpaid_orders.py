"""未決済注文の自動キャンセル

実行頻度: 5分ごと（python manage.py cancel_unpaid_orders）
仕様: api-spec.md「3. 定期実行」・「7. 実装で決めたこと」ステップ6a

ふだんは Stripe の Webhook（checkout.session.expired など）で注文が failed になる。このバッチは、Webhook が
届かなかったときの保険。注文から35分以上たっても pending のままの注文について、Stripe の支払いページの状態を確かめる:
  - 支払いページがまだ開いている → Stripe で期限切れにしてから failed（在庫を戻し、購入者にメール）
  - 支払いページが期限切れ → failed
  - 支払い済み → paid（購入者と生産者にメール）
  - コンビニ払いの支払い待ち → そのまま（PaymentIntent の ID だけ保存。期限切れは Webhook で受け取る）
  - 支払いページがない（作れなかった・開発用に Stripe なしで作った）→ failed
  - Stripe に問い合わせられなかった → その注文は飛ばして、次の回にやり直す
カード払い・コンビニ払いどちらも Checkout で同じ流れになるので、支払い方法では分けない。
更新は services/orders.py の fail_order・mark_paid（pending のときだけ変える）を使う。
"""
import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from api.services import orders, payments
from marche.models import Order

logger = logging.getLogger(__name__)

UNPAID_AFTER = timedelta(minutes=35)  # 支払いページの有効期限（約30分）＋余裕


class Command(BaseCommand):
    help = "注文から35分たっても支払いが始まっていない注文を取り消す（5分ごと）"

    def handle(self, *args, **options):
        deadline = timezone.now() - UNPAID_AFTER
        targets = list(Order.objects.filter(payment_status=Order.PaymentStatus.PENDING, ordered_at__lt=deadline)
                       .order_by("id").values_list("id", "stripe_checkout_session_id"))
        counts = {"failed": 0, "paid": 0, "waiting": 0, "skipped": 0}
        for order_id, session_id in targets:
            counts[self.check_order(order_id, session_id)] += 1
        self.stdout.write("未決済注文の確認: " + " ".join(f"{key}={value}" for key, value in counts.items()))

    def check_order(self, order_id, session_id):
        if not session_id:
            orders.fail_order(order_id, reason="expired")
            return "failed"
        if not payments.is_enabled():
            return "skipped"
        try:
            session = payments.retrieve_checkout_session(session_id)
            if session["status"] == "open":
                session = payments.expire_checkout_session(session_id)
        except payments.PaymentError:
            logger.exception("Stripe の支払いページを確認できませんでした: order_id=%s", order_id)
            return "skipped"

        if session["status"] == "complete":
            if session["payment_status"] == "paid":
                orders.mark_paid(order_id, session["payment_intent"])
                return "paid"
            orders.save_payment_intent(order_id, session["payment_intent"])
            return "waiting"
        orders.fail_order(order_id, reason="expired")
        return "failed"
