"""カート

認証: ゲスト可（会員は user_id、ゲストは session_key のカート → services/cart.py）
仕様: Notion の各API定義＋api-spec.md「7. 実装で決めたこと」ステップ5。カラム名: claude/er-diagram.md
データを変えるリクエストは、ゲストでも CSRF を確認する（認証クラスが自動でやる）。ETag・If-Match は使わない。

このファイルの API（シーケンス図は Notion の「カート」）:
    - カート取得: GET /api/v1/cart
        ・明細（カートに入れた順）・箱（生産者×温度帯）ごとの小計と送料・合計・canCheckout
        ・ゲストでセッションがなければ空のカート（ここではセッションを作らない）
    - カートに追加: POST /api/v1/cart/items
        ・{productId, quantity}。同じ商品は今の数量に足す。合計10個を超えたら 400
        ・公開中でない商品は 404 PRODUCT_NOT_FOUND。自分の商品は 409 CANNOT_PURCHASE_OWN
          定期便は 409 UNSUPPORTED_PRODUCT。在庫0は 409 OUT_OF_STOCK、在庫より多いと 409 QUANTITY_EXCEEDS_STOCK
          商品が50種類を超えると 409 CART_LIMIT_EXCEEDED
        ・ゲストでセッションがなければ、ここで作る。在庫は減らさない（減らすのは注文のとき）。200 でカート全体
    - 数量変更: PATCH /api/v1/cart/items/:itemId
        ・{quantity}（変更後の数、1〜10）。確認は追加と同じ（非公開になった商品は 409 PRODUCT_UNAVAILABLE）
        ・失敗したら数量は変えない。自分のカートの明細でなければ 404 CART_ITEM_NOT_FOUND。200 でカート全体
    - 削除: DELETE /api/v1/cart/items/:itemId
        ・非公開になった商品の明細も消せる。自分の明細でなければ 404。204
"""
from django.db import IntegrityError, transaction
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from marche.models import CartItem

from ...common.exceptions import ApiError, Conflict
from ...common.pagination import validate_query
from ...common.serializers import QuerySerializer, StrictSerializer
from ...serializers.public.cart import MAX_ID, CartItemAddSerializer, CartItemUpdateSerializer
from ...services.cart import MAX_CART_LINES, MAX_QUANTITY, build_cart, cart_owner
from ...services.visibility import public_products


def cart_item_not_found():
    return ApiError(status.HTTP_404_NOT_FOUND, "CART_ITEM_NOT_FOUND", "カートの商品が見つかりません。")


def ensure_can_buy(product, quantity, user):
    """この数量で購入できるか（カートへの追加・数量変更で使う）。できなければ 409"""
    if user.is_authenticated and product.producer.user_id == user.pk:
        raise Conflict("CANNOT_PURCHASE_OWN", "ご自身の商品は購入できません。")
    if product.is_subscription:
        raise Conflict("UNSUPPORTED_PRODUCT", "定期便の商品は、現在カートからは購入できません。")
    if product.stock == 0:
        raise Conflict("OUT_OF_STOCK", "この商品は売り切れです。")
    if product.stock is not None and quantity > product.stock:
        raise Conflict("QUANTITY_EXCEEDS_STOCK", f"在庫が足りません（残り{product.stock}個）。")


def too_many(quantity):
    return serializers.ValidationError({"quantity": [f"1つの商品は{MAX_QUANTITY}個までです。"]}) \
        if quantity > MAX_QUANTITY else None


class CartView(APIView):
    """GET /api/v1/cart"""

    permission_classes = [AllowAny]

    def get(self, request):
        validate_query(QuerySerializer, request)  # クエリパラメーターは受け付けない
        return Response(build_cart(cart_owner(request)))


class CartItemListView(APIView):
    """POST /api/v1/cart/items"""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = CartItemAddSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product_id, quantity = serializer.validated_data["product_id"], serializer.validated_data["quantity"]
        product = public_products().select_related("producer").filter(pk=product_id).first()
        if product is None:
            raise ApiError(status.HTTP_404_NOT_FOUND, "PRODUCT_NOT_FOUND", "商品が見つかりません。")
        owner = cart_owner(request, create=True)

        for attempt in range(2):  # 同時に同じ商品が追加されたら（一意制約の違反）、もう一度足し直す
            try:
                with transaction.atomic():
                    self.add(owner, product, quantity, request.user)
                break
            except IntegrityError:
                if attempt:
                    raise
        return Response(build_cart(owner))

    def add(self, owner, product, quantity, user):
        existing = CartItem.objects.select_for_update().filter(**owner, product=product).first()
        total = (existing.quantity if existing else 0) + quantity
        error = too_many(total)
        if error:
            raise error
        ensure_can_buy(product, total, user)
        if existing:
            existing.quantity = total
            existing.save(update_fields=["quantity", "updated_at"])
            return
        if CartItem.objects.filter(**owner).count() >= MAX_CART_LINES:
            raise Conflict("CART_LIMIT_EXCEEDED", f"カートに入れられる商品は{MAX_CART_LINES}種類までです。")
        CartItem.objects.create(**owner, product=product, quantity=total)


class CartItemDetailView(APIView):
    """PATCH・DELETE /api/v1/cart/items/:itemId"""

    permission_classes = [AllowAny]

    def get_item(self, owner, item_id, lock=False):
        if owner is None or item_id > MAX_ID:
            raise cart_item_not_found()
        queryset = CartItem.objects.filter(**owner)
        if lock:
            queryset = queryset.select_for_update()
        item = queryset.select_related("product__producer").filter(pk=item_id).first()
        if item is None:
            raise cart_item_not_found()
        return item

    def patch(self, request, item_id):
        serializer = CartItemUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        quantity = serializer.validated_data["quantity"]
        owner = cart_owner(request)
        with transaction.atomic():
            item = self.get_item(owner, item_id, lock=True)
            if not public_products().filter(pk=item.product_id).exists():
                raise Conflict("PRODUCT_UNAVAILABLE", "この商品は現在購入できません。カートから削除してください。")
            ensure_can_buy(item.product, quantity, request.user)
            item.quantity = quantity
            item.save(update_fields=["quantity", "updated_at"])
        return Response(build_cart(owner))

    def delete(self, request, item_id):
        StrictSerializer(data=request.data or {}).is_valid(raise_exception=True)  # 本文は受け付けない
        owner = cart_owner(request)
        with transaction.atomic():
            self.get_item(owner, item_id, lock=True).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
