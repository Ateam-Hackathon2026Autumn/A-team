"""お気に入り（生産者フォローを兼ねる）

認証: 会員（ログイン必須。データを変えるリクエストは CSRF も確認する。メール未確認でも使える）
仕様: api-spec.md「お気に入り」＋「7. 実装で決めたこと」（Notion には定義なし）。シーケンス図は Notion の「お気に入り」

このファイルの API:
    - お気に入り一覧: GET /api/v1/users/me/favorites
        ・type=product・producer（必須）。お気に入りに登録した新しい順（created_at・id の降順）。ページングは共通の形
        ・非公開・掲載停止・退会などで公開されなくなったものも残し、isPublic=false で返す
    - 商品お気に入り登録: PUT /api/v1/users/me/favorites/products/:productId
        ・公開中の商品だけ（それ以外は 404 PRODUCT_NOT_FOUND）。自分の商品は 409 CANNOT_FAVORITE_OWN
        ・登録済みでもエラーにしない。204
    - 商品お気に入り解除: DELETE /api/v1/users/me/favorites/products/:productId
        ・公開状態を見ずに消す。未登録・存在しない ID でも 204
    - 生産者お気に入り登録: PUT /api/v1/users/me/favorites/producers/:producerId
        ・{notify}（省略可）。公開中の生産者だけ（それ以外は 404 PRODUCER_NOT_FOUND）。自分の農園は 409
        ・新しく登録するときの notify の初期値は false。登録済みなら、notify を送ったときだけ更新する。204
    - 生産者お気に入り解除: DELETE /api/v1/users/me/favorites/producers/:producerId
        ・公開状態を見ずに消す。未登録でも 204

件数の上限はない。本文を受け付けない API に項目が来たら 400。
"""
from django.db import IntegrityError, transaction
from django.db.models import Exists, OuterRef, Subquery
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from marche.models import FavoriteProducer, FavoriteProduct, ProducerStory, ProductImage, PublishStatus

from ...common.exceptions import ApiError, Conflict
from ...common.pagination import paginate, validate_query
from ...common.serializers import StrictSerializer
from ...serializers.public.favorites import (
    FavoriteListQuerySerializer,
    FavoriteProducerBodySerializer,
    FavoriteProducerItemSerializer,
    FavoriteProductItemSerializer,
)
from ...services.visibility import public_producers, public_products

MAX_ID = 2 ** 63 - 1


def cannot_favorite_own():
    return Conflict("CANNOT_FAVORITE_OWN", "ご自身の商品・農園はお気に入りに登録できません。")


def validate_empty_body(request):
    StrictSerializer(data=request.data or {}).is_valid(raise_exception=True)


def favorite_products(user):
    """お気に入り商品（商品カードの項目は JOIN とサブクエリで1本の SQL にする）"""
    thumbnail = (ProductImage.objects.filter(product=OuterRef("product_id"))
                 .order_by("sort_order", "id").values("image")[:1])
    return (FavoriteProduct.objects.filter(user=user)
            .select_related("product__category", "product__producer__prefecture")
            .annotate(thumbnail_key=Subquery(thumbnail),
                      is_public=Exists(public_products().filter(pk=OuterRef("product_id")))))


def favorite_producers(user):
    """お気に入り生産者（生産者カードの項目は JOIN とサブクエリで1本の SQL にする）"""
    public_story = ProducerStory.objects.filter(producer=OuterRef("producer_id"), publish_status=PublishStatus.PUBLIC)
    return (FavoriteProducer.objects.filter(user=user)
            .select_related("producer__prefecture")
            .annotate(has_public_story=Exists(public_story),
                      is_public=Exists(public_producers().filter(pk=OuterRef("producer_id")))))


class FavoriteListView(APIView):
    """GET /api/v1/users/me/favorites"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = validate_query(FavoriteListQuerySerializer, request)
        if query["type"] == "product":
            favorites, serializer = favorite_products(request.user), FavoriteProductItemSerializer
        else:
            favorites, serializer = favorite_producers(request.user), FavoriteProducerItemSerializer
        count = favorites.model.objects.filter(user=request.user)
        return Response(paginate(favorites.order_by("-created_at", "-id"), query, serializer,
                                 context={"now": timezone.now()}, count_queryset=count))


class FavoriteProductView(APIView):
    """PUT・DELETE /api/v1/users/me/favorites/products/:productId"""

    permission_classes = [IsAuthenticated]

    def put(self, request, product_id):
        validate_empty_body(request)
        product = (public_products().select_related("producer").filter(pk=product_id).first()
                   if product_id <= MAX_ID else None)
        if product is None:
            raise ApiError(status.HTTP_404_NOT_FOUND, "PRODUCT_NOT_FOUND", "商品が見つかりません。")
        if product.producer.user_id == request.user.pk:
            raise cannot_favorite_own()
        try:
            with transaction.atomic():
                FavoriteProduct.objects.get_or_create(user=request.user, product=product)
        except IntegrityError:
            pass  # 同時に登録された（すでに登録済みと同じ）
        return Response(status=status.HTTP_204_NO_CONTENT)

    def delete(self, request, product_id):
        validate_empty_body(request)
        if product_id <= MAX_ID:
            FavoriteProduct.objects.filter(user=request.user, product_id=product_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class FavoriteProducerView(APIView):
    """PUT・DELETE /api/v1/users/me/favorites/producers/:producerId"""

    permission_classes = [IsAuthenticated]

    def put(self, request, producer_id):
        serializer = FavoriteProducerBodySerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        producer = public_producers().filter(pk=producer_id).first() if producer_id <= MAX_ID else None
        if producer is None:
            raise ApiError(status.HTTP_404_NOT_FOUND, "PRODUCER_NOT_FOUND", "生産者が見つかりません。")
        if producer.user_id == request.user.pk:
            raise cannot_favorite_own()

        notify = serializer.validated_data.get("notify")
        try:
            with transaction.atomic():
                favorite, created = FavoriteProducer.objects.select_for_update().get_or_create(
                    user=request.user, producer=producer, defaults={"notify": bool(notify)})
                if not created and notify is not None and favorite.notify != notify:
                    favorite.notify = notify
                    favorite.save(update_fields=["notify", "updated_at"])
        except IntegrityError:
            pass  # 同時に登録された（すでに登録済みと同じ）
        return Response(status=status.HTTP_204_NO_CONTENT)

    def delete(self, request, producer_id):
        validate_empty_body(request)
        if producer_id <= MAX_ID:
            FavoriteProducer.objects.filter(user=request.user, producer_id=producer_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
