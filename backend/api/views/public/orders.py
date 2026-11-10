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
         会員は shippingAddress の代わりに addressId（住所録）も使える（どちらか一方。他人の住所は 400）
      2. トランザクションの中で、カートの中身から注文を作り、在庫を減らし、カートを空にする（create_order）
         409: CART_EMPTY / QUOTE_CHANGED / CANNOT_PURCHASE_OWN / PAYMENT_METHOD_NOT_AVAILABLE
      3. トランザクションの外で Stripe Checkout（支払いページ）を作り、セッションIDを保存する
         作れなかったら注文を failed にし、在庫とカートを元に戻して 503 PAYMENT_UNAVAILABLE
      4. 201 {id, orderNo, paymentStatus（pending）, itemsTotal, shippingTotal, grandTotal, checkoutUrl, expiresAt}
         支払いの確定（paid）は Webhook だけで行う（支払いページから戻ってきたことでは確定しない）
      ・STRIPE_SECRET_KEY が空なら 503 PAYMENT_UNAVAILABLE（注文は作らない）。ただし DEBUG のときだけは、Stripe を使わずに
        注文を作り、checkoutUrl に注文完了画面のURLを返す（支払い済みにするのは python manage.py mark_order_paid）
      ・同じIPから1時間30回まで（回数制限 order）

  - 注文履歴一覧（会員）: GET /api/v1/users/me/orders
      ・自分の注文だけ（ゲスト時代の注文はメールが同じでも含めない）。pending・failed も含める
      ・paymentStatus で絞り込み。ordered_at・id の降順。ページングは共通の形。箱は id 順
  - 注文詳細（会員）: GET /api/v1/users/me/orders/:orderId
      ・他人の注文・存在しない注文は 404 ORDER_NOT_FOUND
      ・箱ごとに cancellable（注文が paid で、その生産者の箱がすべて unshipped）
  - キャンセル申請（会員）: POST /api/v1/users/me/orders/:orderId/cancel
      ・{producerId, cancelReason（1〜500文字）}。その生産者の箱をまとめて cancel_requested にし、生産者に通知・メール
      ・できなければ 409 CANCEL_NOT_ALLOWED（支払い前・発送済みの箱がある・申請済みなど）。注文にない生産者は 400
      ・生産者が掲載停止中でも申請できる。200 で更新後の注文詳細
  - 注文詳細（ゲスト）: GET /api/v1/orders/:orderId
  - キャンセル申請（ゲスト）: POST /api/v1/orders/:orderId/cancel
      ・ヘッダー X-Order-Token のトークンを SHA-256 にして access_token_hash と照合する。照合できるのはゲストの注文
        （user_id が空）だけ。トークンがない・違う・会員の注文は、区別せず 404 ORDER_NOT_FOUND
      ・ログイン中でも使える（トークン自体が見てよい証明）。返す内容とキャンセルのルールは会員と同じ。
        詳細には購入者の連絡先 buyer {name, email, phone} も返す
"""
import logging
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone

from django.conf import settings
from django.db.models import Prefetch
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from marche.models import Order, OrderItem, OrderShipment

from ...common.exceptions import ApiError, Conflict
from ...common.pagination import paginate, validate_query
from ...common.throttles import IPRateThrottle
from ...serializers.public.orders import (
    MAX_ID,
    CancelRequestSerializer,
    GuestOrderCreateSerializer,
    GuestOrderDetailSerializer,
    MyOrderDetailSerializer,
    MyOrderListQuerySerializer,
    MyOrderSummarySerializer,
    OrderCreateSerializer,
)
from ...services import mail, payments
from ...services.cart import cart_owner
from ...services.orders import (
    cancellable_producer_ids,
    checkout_lines,
    create_order,
    hash_token,
    request_cancel,
    undo_order,
)

logger = logging.getLogger(__name__)

DEV_CHECKOUT_TTL = timedelta(minutes=30)


class BaseOrderCreateView(APIView):
    throttle_classes = [IPRateThrottle]
    throttle_scope = "order"
    serializer_class = None

    def place_order(self, request, user, guest_key=None):
        serializer = self.serializer_class(data=request.data, context={"user": user})
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


# =========================================================
# 注文履歴・詳細・キャンセル申請
# =========================================================

ORDER_TOKEN_HEADER = "HTTP_X_ORDER_TOKEN"
MAX_TOKEN_LENGTH = 200


def order_not_found():
    return ApiError(status.HTTP_404_NOT_FOUND, "ORDER_NOT_FOUND", "注文が見つかりません。")


def detail_queryset():
    items = OrderItem.objects.select_related("review").order_by("id")
    shipments = (OrderShipment.objects.select_related("producer")
                 .prefetch_related(Prefetch("order_items", queryset=items)).order_by("id"))
    return Order.objects.prefetch_related(Prefetch("order_shipments", queryset=shipments))


def detail_response(order, serializer_class):
    shipments = order.order_shipments.all()
    context = {"cancellable_producer_ids": cancellable_producer_ids(order, shipments)}
    return Response(serializer_class(order, context=context).data)


class MyOrderListView(APIView):
    """GET /api/v1/users/me/orders"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = validate_query(MyOrderListQuerySerializer, request)
        orders = Order.objects.filter(user=request.user)
        if query.get("payment_status"):
            orders = orders.filter(payment_status=query["payment_status"])
        shipments = OrderShipment.objects.select_related("producer").order_by("id")
        items = orders.prefetch_related(Prefetch("order_shipments", queryset=shipments)).order_by("-ordered_at", "-id")
        return Response(paginate(items, query, MyOrderSummarySerializer, count_queryset=orders))


class MyOrderAccessMixin:
    """会員：自分の注文だけ"""

    detail_serializer_class = MyOrderDetailSerializer

    def find_order(self, request, order_id):
        if order_id > MAX_ID:
            raise order_not_found()
        order = detail_queryset().filter(pk=order_id, user=request.user).first()
        if order is None:
            raise order_not_found()
        return order


class GuestOrderAccessMixin:
    """ゲスト：X-Order-Token のトークンで照合する（ゲストの注文だけ）"""

    detail_serializer_class = GuestOrderDetailSerializer

    def find_order(self, request, order_id):
        token = request.META.get(ORDER_TOKEN_HEADER, "")
        if not token or len(token) > MAX_TOKEN_LENGTH or order_id > MAX_ID:
            raise order_not_found()
        order = detail_queryset().filter(pk=order_id, user__isnull=True, access_token_hash=hash_token(token)).first()
        if order is None:
            raise order_not_found()
        return order


class BaseOrderDetailView(APIView):
    def get(self, request, order_id):
        return detail_response(self.find_order(request, order_id), self.detail_serializer_class)


class BaseOrderCancelView(APIView):
    def post(self, request, order_id):
        order = self.find_order(request, order_id)
        serializer = CancelRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        request_cancel(order.pk, data["producer_id"], data["cancel_reason"])
        return detail_response(self.find_order(request, order_id), self.detail_serializer_class)


class MyOrderDetailView(MyOrderAccessMixin, BaseOrderDetailView):
    """GET /api/v1/users/me/orders/:orderId"""

    permission_classes = [IsAuthenticated]


class MyOrderCancelView(MyOrderAccessMixin, BaseOrderCancelView):
    """POST /api/v1/users/me/orders/:orderId/cancel"""

    permission_classes = [IsAuthenticated]


class GuestOrderDetailView(GuestOrderAccessMixin, BaseOrderDetailView):
    """GET /api/v1/orders/:orderId"""

    permission_classes = [AllowAny]


class GuestOrderCancelView(GuestOrderAccessMixin, BaseOrderCancelView):
    """POST /api/v1/orders/:orderId/cancel"""

    permission_classes = [AllowAny]
