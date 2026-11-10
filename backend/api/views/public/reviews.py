"""商品レビュー（一覧・投稿・編集・削除）

認証: 一覧は公開。投稿・編集・削除は会員（未ログインは 401）。メール未確認でも使える
仕様: api-spec.md「7. 実装で決めたこと」ステップ10（Notion にはシーケンス図「レビュー」と名前だけ）。
カラム名: claude/er-diagram.md。体験レビューは拡張

実装済み:
  - 商品レビュー一覧: GET /api/v1/products/:productId/reviews
      ・公開中の商品だけ（ほかは 404 PRODUCT_NOT_FOUND）。created_at・id の降順。ページングは共通の形＋canReview
      ・canReview はログイン中で、この商品にまだレビューしていない発送済みの購入があれば true
  - レビュー投稿: POST /api/v1/products/:productId/reviews
      ・{rating, body, orderItemId（任意）}。公開中の商品だけ。services/reviews.py の create_review。201 でレビュー
  - レビュー編集: PATCH /api/v1/users/me/reviews/:reviewId（送った項目だけ。200）
  - レビュー削除: DELETE /api/v1/users/me/reviews/:reviewId（204）
      ・編集・削除は期限なし。商品が非公開になっても自分のレビューなら使える。他人のレビューは 404 REVIEW_NOT_FOUND
      ・どちらも商品の評価を集計し直す（0件なら rating_avg は空）
"""
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from marche.models import ProductReview

from ...common.exceptions import ApiError
from ...common.pagination import PageQuerySerializer, paginate, validate_query
from ...serializers.public.reviews import (
    MAX_ID,
    ReviewCreateSerializer,
    ReviewSerializer,
    ReviewUpdateSerializer,
)
from ...services.reviews import create_review, delete_review, review_not_found, reviewable_items, update_review
from ...services.visibility import public_products


def product_not_found():
    return ApiError(status.HTTP_404_NOT_FOUND, "PRODUCT_NOT_FOUND", "商品が見つかりません。")


def ensure_public_product(product_id):
    if product_id > MAX_ID or not public_products().filter(pk=product_id).exists():
        raise product_not_found()


class ProductReviewListCreateView(APIView):
    """GET・POST /api/v1/products/:productId/reviews"""

    def get_permissions(self):
        return [IsAuthenticated()] if self.request.method == "POST" else [AllowAny()]

    def get(self, request, product_id):
        query = validate_query(PageQuerySerializer, request)
        ensure_public_product(product_id)
        reviews = ProductReview.objects.filter(product_id=product_id)
        items = reviews.select_related("user").order_by("-created_at", "-id")
        body = paginate(items, query, ReviewSerializer, count_queryset=reviews)
        body["can_review"] = (request.user.is_authenticated
                              and reviewable_items(request.user, product_id).exists())
        return Response(body)

    def post(self, request, product_id):
        serializer = ReviewCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ensure_public_product(product_id)
        review = create_review(product_id, request.user, serializer.validated_data)
        review = ProductReview.objects.select_related("user").get(pk=review.pk)
        return Response(ReviewSerializer(review).data, status=status.HTTP_201_CREATED)


class MyReviewDetailView(APIView):
    """PATCH・DELETE /api/v1/users/me/reviews/:reviewId"""

    permission_classes = [IsAuthenticated]

    def patch(self, request, review_id):
        serializer = ReviewUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if review_id > MAX_ID:
            raise review_not_found()
        review = update_review(review_id, request.user, serializer.validated_data)
        review = ProductReview.objects.select_related("user").get(pk=review.pk)
        return Response(ReviewSerializer(review).data)

    def delete(self, request, review_id):
        if review_id > MAX_ID:
            raise review_not_found()
        delete_review(review_id, request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
