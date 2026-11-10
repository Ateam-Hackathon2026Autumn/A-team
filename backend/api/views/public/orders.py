"""注文・注文履歴・キャンセル申請（会員・ゲスト）

認証: 会員（POST /orders）／ゲスト（POST /guest/orders）
仕様: Notion の「注文・決済API」＋api-spec.md「7. 実装で決めたこと」ステップ6a。カラム名: claude/er-diagram.md
データを変えるリクエストは、ゲストでも CSRF を確認する（認証クラスが自動でやる）。

実装済み（シーケンス図は Notion の「注文・決済・注文履歴」）:
  - 注文・決済（会員）: POST /api/v1/orders
      ・未ログインは 401。メール未確認でも注文できる
  - 注文・決済（ゲスト）: POST /api/v1/guest/orders
      ・ログイン中は 409 ALREADY_AUTHENTICATED。guestContact（姓・名・メール・電話）が必須
  - 2本とも同じ流れ（services/orders.py・services/payments.py）:
      1. 本文 {shippingAddress, paymentMethod（card・konbini）, expectedGrandTotal}（ゲストは guestContact も）を検証
      2. トランザクションの中で、カートの中身から注文を作り、在庫を減らし、カートを空にする（create_order）
         409: CART_EMPTY / QUOTE_CHANGED / CANNOT_PURCHASE_OWN / PAYMENT_METHOD_NOT_AVAILABLE
      3. トランザクションの外で Stripe Checkout（支払いページ）を作り、セッションIDを保存する
         作れなかったら注文を failed にし、在庫とカートを元に戻して 503 PAYMENT_UNAVAILABLE
      4. 201 {id, orderNo, paymentStatus（pending）, itemsTotal, shippingTotal, grandTotal, checkoutUrl, expiresAt}
         支払いの確定（paid）は Webhook だけで行う（支払いページから戻ってきたことでは確定しない）
      ・STRIPE_SECRET_KEY が空なら 503 PAYMENT_UNAVAILABLE（注文は作らない）。ただし DEBUG のときだけは、Stripe を使わずに
        注文を作り、checkoutUrl に注文完了画面のURLを返す（支払い済みにするのは python manage.py mark_order_paid）
      ・同じIPから1時間30回まで（回数制限 order）

これから書くもの（ステップ6b）:
  - 注文履歴一覧: GET /api/v1/users/me/orders
  - 注文詳細: GET /api/v1/users/me/orders/:orderId
  - キャンセル申請（会員）: POST /api/v1/users/me/orders/:orderId/cancel
  - 注文詳細（ゲスト）: GET /api/v1/orders/:orderId（X-Order-Token のトークンを SHA-256 にして access_token_hash と照合）
  - キャンセル申請（ゲスト）: POST /api/v1/orders/:orderId/cancel
"""
import logging
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone

from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from marche.models import Order

from ...common.exceptions import Conflict
from ...common.throttles import IPRateThrottle
from ...serializers.public.orders import GuestOrderCreateSerializer, OrderCreateSerializer
from ...services import mail, payments
from ...services.cart import cart_owner
from ...services.orders import checkout_lines, create_order, undo_order

logger = logging.getLogger(__name__)

DEV_CHECKOUT_TTL = timedelta(minutes=30)


class BaseOrderCreateView(APIView):
    throttle_classes = [IPRateThrottle]
    throttle_scope = "order"
    serializer_class = None

    def place_order(self, request, user, guest_key=None):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        guest = data.get(guest_key) if guest_key else None
        stripe_enabled = payments.is_enabled()
        if not stripe_enabled and not settings.DEBUG:
            raise payments.payment_unavailable()

        owner = cart_owner(request)
        order = create_order(owner, user, guest, data["shipping_address"], data["payment_method"],
                             data["expected_grand_total"])

        if stripe_enabled:
            email = user.email if user is not None else guest["email"]
            try:
                session = payments.create_checkout_session(order, checkout_lines(order), email)
            except payments.PaymentError:
                undo_order(order, owner)
                raise payments.payment_unavailable()
            Order.objects.filter(pk=order.pk).update(stripe_checkout_session_id=session["id"],
                                                     updated_at=timezone.now())
            checkout_url = session["url"]
            expires_at = datetime.fromtimestamp(session["expires_at"], tz=dt_timezone.utc)
        else:
            # 開発用（DEBUG かつ STRIPE_SECRET_KEY が空）：支払いページの代わりに注文完了画面へ
            logger.warning("Stripe のキーがないため、支払いページを作らずに注文を作りました: %s", order.order_no)
            checkout_url = mail.frontend_url(payments.SUCCESS_PATH, orderId=order.id)
            expires_at = order.ordered_at + DEV_CHECKOUT_TTL

        return Response({
            "id": order.id, "order_no": order.order_no, "payment_status": order.payment_status,
            "items_total": order.items_total, "shipping_total": order.shipping_total,
            "grand_total": order.grand_total, "checkout_url": checkout_url,
            "expires_at": timezone.localtime(expires_at),
        }, status=status.HTTP_201_CREATED)


class OrderCreateView(BaseOrderCreateView):
    """POST /api/v1/orders（会員）"""

    permission_classes = [IsAuthenticated]
    serializer_class = OrderCreateSerializer

    def post(self, request):
        return self.place_order(request, request.user)


class GuestOrderCreateView(BaseOrderCreateView):
    """POST /api/v1/guest/orders（ゲスト）"""

    permission_classes = [AllowAny]
    serializer_class = GuestOrderCreateSerializer

    def post(self, request):
        if request.user.is_authenticated:
            raise Conflict("ALREADY_AUTHENTICATED", "ログイン中です。会員の注文画面からご注文ください。")
        return self.place_order(request, None, guest_key="guest_contact")
