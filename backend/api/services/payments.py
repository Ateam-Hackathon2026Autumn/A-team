"""Stripe との連携（支払いページ＝Stripe Checkout）

view・バッチから呼ぶ。Stripe のオブジェクトはここで普通の dict に直して返すので、呼び出し側（とテスト）は
Stripe のライブラリを知らなくてよい。テストではこのファイルの関数を unittest.mock.patch で差し替える。

実装済み:
  - is_enabled(): STRIPE_SECRET_KEY が設定されているか
  - create_checkout_session(order, lines, email): 支払いページを作る（有効期限30分。コンビニ払いは支払い期限3日）
      → {"id", "url", "expires_at"}。Stripe の重複防止キーは order-{注文ID}-checkout
  - retrieve_checkout_session(session_id) / expire_checkout_session(session_id): 状態の確認・期限切れにする
      → {"id", "status"（open / complete / expired）, "payment_status"（paid / unpaid）, "payment_intent", "order_id"}
  - parse_webhook(payload, signature): 署名を検証して (イベントの種類, セッションの dict) を返す。不正なら InvalidWebhook
  - Stripe のエラーは PaymentError にまとめる（view は 503 PAYMENT_UNAVAILABLE にする）

これから追加するもの（ステップ6b）:
  - 箱ごとの部分返金（api-spec「Stripe 返金（未実装・決定済み）」）

使う場所: POST /orders・POST /guest/orders、POST /webhooks/stripe、未決済注文の自動キャンセル（バッチ）
"""
import logging
import time

import stripe
from django.conf import settings
from rest_framework import status

from ..common.exceptions import ApiError
from . import mail

logger = logging.getLogger(__name__)

CHECKOUT_TTL_SECONDS = 30 * 60 + 60  # 支払いページの有効期限。Stripe の下限が30分なので、少しだけ余裕を持たせる
KONBINI_EXPIRES_AFTER_DAYS = 3  # コンビニ払いの支払い期限（日）

# 支払いページから戻る先（フロントの画面）。{order_id} を注文IDに置き換える
SUCCESS_PATH = "/checkout/complete"
CANCEL_PATH = "/checkout"


class PaymentError(Exception):
    """Stripe との通信に失敗した（障害・設定ミスなど）"""


class InvalidWebhook(Exception):
    """Webhook の署名が合わない・本文が壊れている"""


def payment_unavailable():
    return ApiError(status.HTTP_503_SERVICE_UNAVAILABLE, "PAYMENT_UNAVAILABLE",
                    "決済サービスに接続できません。時間をおいて再度お試しください。")


def is_enabled():
    return bool(settings.STRIPE_SECRET_KEY)


def _session_dict(session):
    if hasattr(session, "to_dict"):  # Stripe のオブジェクトは dict ではないので、普通の dict に直す
        session = session.to_dict()
    metadata = session.get("metadata") or {}
    payment_intent = session.get("payment_intent")
    if payment_intent is not None and not isinstance(payment_intent, str):
        payment_intent = payment_intent.get("id")
    return {
        "id": session.get("id"),
        "status": session.get("status"),
        "payment_status": session.get("payment_status"),
        "payment_intent": payment_intent,
        "order_id": metadata.get("order_id") or session.get("client_reference_id"),
    }


def create_checkout_session(order, lines, email):
    """支払いページを作る。lines は [(商品名, 割引後の単価, 数量)]。送料は1行にまとめる"""
    line_items = [
        {"price_data": {"currency": "jpy", "unit_amount": price, "product_data": {"name": name}}, "quantity": quantity}
        for name, price, quantity in lines
    ]
    if order.shipping_total:
        line_items.append({"price_data": {"currency": "jpy", "unit_amount": order.shipping_total,
                                          "product_data": {"name": "送料"}}, "quantity": 1})
    metadata = {"order_id": str(order.id), "order_no": order.order_no}
    params = {
        "mode": "payment",
        "line_items": line_items,
        "payment_method_types": [order.payment_method],
        "customer_email": email,
        "client_reference_id": str(order.id),
        "metadata": metadata,
        "payment_intent_data": {"metadata": metadata},  # 返金の照合用（PaymentIntent 側にも注文IDを残す）
        "expires_at": int(time.time()) + CHECKOUT_TTL_SECONDS,
        "locale": "ja",
        "success_url": mail.frontend_url(SUCCESS_PATH, orderId=order.id),
        "cancel_url": mail.frontend_url(CANCEL_PATH, canceledOrderId=order.id),
    }
    if order.payment_method == "konbini":
        params["payment_method_options"] = {"konbini": {"expires_after_days": KONBINI_EXPIRES_AFTER_DAYS}}
    try:
        session = stripe.checkout.Session.create(
            api_key=settings.STRIPE_SECRET_KEY, idempotency_key=f"order-{order.id}-checkout", **params)
    except stripe.StripeError as exc:
        logger.exception("Stripe Checkout の作成に失敗しました: order_id=%s", order.id)
        raise PaymentError(str(exc)) from exc
    return {"id": session["id"], "url": session["url"], "expires_at": session["expires_at"]}


def retrieve_checkout_session(session_id):
    try:
        session = stripe.checkout.Session.retrieve(session_id, api_key=settings.STRIPE_SECRET_KEY)
    except stripe.StripeError as exc:
        raise PaymentError(str(exc)) from exc
    return _session_dict(session)


def expire_checkout_session(session_id):
    """支払いページを期限切れにする（もう支払えなくする）。開いているときだけ使える"""
    try:
        session = stripe.checkout.Session.expire(session_id, api_key=settings.STRIPE_SECRET_KEY)
    except stripe.StripeError as exc:
        raise PaymentError(str(exc)) from exc
    return _session_dict(session)


def parse_webhook(payload, signature):
    """署名を検証し、(イベントの種類, セッションの dict) を返す。Checkout 以外のイベントのセッションは None"""
    try:
        event = stripe.Webhook.construct_event(payload, signature, settings.STRIPE_WEBHOOK_SECRET)
    except (ValueError, stripe.SignatureVerificationError) as exc:
        raise InvalidWebhook(str(exc)) from exc
    event_type = event["type"]
    obj = event["data"]["object"]
    session = _session_dict(obj) if event_type.startswith("checkout.session.") else None
    return event_type, session
