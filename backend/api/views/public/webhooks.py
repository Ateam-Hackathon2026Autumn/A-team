"""Stripe の Webhook

認証: Stripe（Stripe-Signature ヘッダーの署名で確認する。セッション・CSRF は使わない）
仕様: api-spec.md「7. 実装で決めたこと」ステップ6a

実装済み:
  - 決済結果の受信: POST /api/v1/webhooks/stripe
      ・署名が合わない・本文が壊れている → 400 INVALID_SIGNATURE（Stripe が再送する）
      ・checkout.session.completed:
          支払い済み（payment_status=paid）→ paid にし、購入者と生産者にメール（services/orders.py の mark_paid）
          コンビニ払いでまだ支払われていない（unpaid）→ PaymentIntent の ID だけ保存して待つ
      ・checkout.session.async_payment_succeeded → paid（コンビニ払いの入金）
      ・checkout.session.async_payment_failed → failed（在庫を戻し、購入者にメール）
      ・checkout.session.expired → failed（支払いページの期限切れ）
      ・どれも pending の注文だけ更新する。同じイベントが2回届いても、2回目は何もしない。処理記録のテーブルは作らない
      ・知らないイベント・注文が見つからないイベントは何もせず 200（Stripe が再送し続けないように）
"""
import logging

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from marche.models import Order

from ...common.exceptions import ApiError
from ...services import orders, payments

logger = logging.getLogger(__name__)

MAX_ID = 2 ** 63 - 1


def find_order_id(session):
    """セッションの order_id（metadata）と、注文に保存したセッションIDが一致する注文の ID。なければ None"""
    order_id = session.get("order_id")
    if not order_id or not str(order_id).isdigit() or int(order_id) > MAX_ID:
        return None
    order = Order.objects.filter(pk=int(order_id)).only("id", "stripe_checkout_session_id").first()
    if order is None or (order.stripe_checkout_session_id and order.stripe_checkout_session_id != session["id"]):
        return None
    return order.id


class StripeWebhookView(APIView):
    """POST /api/v1/webhooks/stripe"""

    authentication_classes = []  # セッションを使わない（CSRF の確認もしない）
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            event_type, session = payments.parse_webhook(request.body, request.META.get("HTTP_STRIPE_SIGNATURE"))
        except payments.InvalidWebhook:
            raise ApiError(status.HTTP_400_BAD_REQUEST, "INVALID_SIGNATURE", "署名を確認できませんでした。")

        order_id = find_order_id(session) if session else None
        if order_id is None:
            if session:
                logger.warning("Webhook の注文が見つかりません: type=%s session=%s", event_type, session.get("id"))
            return Response({"received": True})

        if event_type == "checkout.session.completed":
            if session["payment_status"] == "paid":
                orders.mark_paid(order_id, session["payment_intent"])
            else:
                orders.save_payment_intent(order_id, session["payment_intent"])
        elif event_type == "checkout.session.async_payment_succeeded":
            orders.mark_paid(order_id, session["payment_intent"])
        elif event_type == "checkout.session.async_payment_failed":
            orders.fail_order(order_id, reason="payment_failed")
        elif event_type == "checkout.session.expired":
            orders.fail_order(order_id, reason="expired")
        return Response({"received": True})
