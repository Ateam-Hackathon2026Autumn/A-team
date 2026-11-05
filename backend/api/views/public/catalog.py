"""商品・カテゴリー（公開側）

認証: 公開（ログイン不要。ログイン中ならお気に入り済みを返す）
仕様: Notion の各API定義＋api-spec.md「7. 実装で決めたこと」ステップ2。カラム名: claude/er-diagram.md

このファイルの API（シーケンス図は Notion の「商品一覧・商品詳細」）:
    - 商品一覧: GET /api/v1/products
        ・公開条件は services/visibility.py（ユーザーが有効・未退会も含む）
        ・categoryId・producerId で絞り込み（両方なら AND）。存在しない・非公開の ID は 200 の空配列
        ・sort: popular（初期値・popularity_score）/ newest（created_at）/ price_asc・price_desc（sale_price）
          / rating（review_count が3件以上を先、その中で rating_avg の降順、null は末尾）。どれも最後に id DESC
        ・ページングは common/pagination.py（件数と一覧は同じ時点で読む）
        ・メイン画像は product_images の sort_order・id の昇順で先頭（サブクエリ）
        ・ログイン中はお気に入り済み（Exists のサブクエリ）。N+1 にしない（件数1本＋一覧1本）
        ・売り切れも表示する。stock は null＝在庫管理しない（購入可）、0＝売り切れ
    - 商品詳細: GET /api/v1/products/:productId
        ・一覧の項目＋説明・生産方法・お届け日時指定・画像・配送設定・craft（生産者ストーリーが公開中のときだけ）
        ・存在しない・公開対象外は区別せず 404 PRODUCT_NOT_FOUND（ログイン中の出品者本人でも同じ）
        ・ID が数字でない URL は URL に一致しないので共通の 404 NOT_FOUND
    - カテゴリー一覧: GET /api/v1/categories
        ・{items: [...]}。sort_order・id の昇順。ページングなし。商品0件のカテゴリーも返す
    - 商品レビュー一覧: GET /api/v1/products/:productId/reviews … ステップ10（レビュー）で書く

未知のクエリパラメーターは 400（どのAPIも）。
"""
from django.db import transaction
from django.db.models import BooleanField, Case, Exists, F, OuterRef, Subquery, Value, When
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from marche.models import Category, FavoriteProduct, ProductImage

from ...common.exceptions import ApiError
from ...common.pagination import paginate, validate_query
from ...common.serializers import QuerySerializer
from ...serializers.public.catalog import (
    MAX_ID,
    CategorySerializer,
    ProductDetailSerializer,
    ProductListQuerySerializer,
    ProductSummarySerializer,
)
from ...services.visibility import public_products

# 並び順。どれも最後に id DESC
SORT_ORDERS = {
    "popular": ["-popularity_score", "-id"],
    "newest": ["-created_at", "-id"],
    "price_asc": ["sale_price", "-id"],
    "price_desc": ["-sale_price", "-id"],
    # レビュー1件で★5の商品が先頭に来ないよう、3件以上の商品を先に並べる
    "rating": ["-has_enough_reviews", F("rating_avg").desc(nulls_last=True), "-id"],
}


def annotate_product_list(queryset, user):
    """商品カードに必要な項目を、一覧と同じ1本の SQL で取れるようにする

    - category・producer・都道府県は JOIN（select_related）
    - thumbnail_key: メイン画像のキー（サブクエリ）
    - is_favorited: ログイン中の会員のお気に入りにあるか（EXISTS のサブクエリ。未ログインは False 固定）
    """
    thumbnail = ProductImage.objects.filter(product=OuterRef("pk")).order_by("sort_order", "id").values("image")[:1]
    if user.is_authenticated:
        is_favorited = Exists(FavoriteProduct.objects.filter(user=user, product=OuterRef("pk")))
    else:
        is_favorited = Value(False, output_field=BooleanField())
    return queryset.select_related("category", "producer__prefecture").annotate(
        thumbnail_key=Subquery(thumbnail),
        is_favorited=is_favorited,
    )


class ProductListView(APIView):
    """GET /api/v1/products"""

    permission_classes = [AllowAny]

    def get(self, request):
        query = validate_query(ProductListQuerySerializer, request)
        queryset = public_products()
        if "category_id" in query:
            queryset = queryset.filter(category_id=query["category_id"])
        if "producer_id" in query:
            queryset = queryset.filter(producer_id=query["producer_id"])

        listed = annotate_product_list(queryset, request.user)
        if query["sort"] == "rating":
            listed = listed.annotate(has_enough_reviews=Case(
                When(review_count__gte=3, then=Value(1)), default=Value(0)))
        listed = listed.order_by(*SORT_ORDERS[query["sort"]])
        # 件数は注釈・JOIN を付ける前の QuerySet で数える
        return Response(paginate(listed, query, ProductSummarySerializer, count_queryset=queryset))


class ProductDetailView(APIView):
    """GET /api/v1/products/:productId"""

    permission_classes = [AllowAny]

    def get(self, request, product_id):
        validate_query(QuerySerializer, request)  # クエリパラメーターは受け付けない
        if product_id > MAX_ID:
            raise_product_not_found()

        # 商品・画像・配送設定・ストーリーを同じ時点で読む
        with transaction.atomic():
            product = (
                annotate_product_list(public_products(), request.user)
                .select_related("shipping_setting", "producer__story")
                .prefetch_related("product_images")
                .filter(pk=product_id)
                .first()
            )
            if product is None:
                raise_product_not_found()
            data = ProductDetailSerializer(product).data
        return Response(data)


def raise_product_not_found():
    raise ApiError(status.HTTP_404_NOT_FOUND, "PRODUCT_NOT_FOUND", "商品が見つかりません。")


class CategoryListView(APIView):
    """GET /api/v1/categories"""

    permission_classes = [AllowAny]

    def get(self, request):
        validate_query(QuerySerializer, request)  # クエリパラメーターは受け付けない
        categories = Category.objects.order_by("sort_order", "id")
        return Response({"items": CategorySerializer(categories, many=True).data})
