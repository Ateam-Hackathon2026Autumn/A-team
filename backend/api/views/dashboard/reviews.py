"""レビュー確認・返信（生産者）

認証: 承認済みの生産者（IsApprovedProducer。未ログイン 401、生産者でない・承認前は 403）
仕様: api-spec.md「7. 実装で決めたこと」ステップ10。カラム名: claude/er-diagram.md

実装済み:
  - レビュー一覧（生産者）: GET /api/v1/dashboard/reviews
      ・自分の商品のレビューを created_at・id の降順。productId・unreplied=true（未返信だけ）で絞り込み
      ・1件はレビュー＋product {id, name}。投稿者は名（first_name）だけ。ページングは共通の形
      ・掲載停止中でも見られる
  - レビュー返信: POST /api/v1/dashboard/reviews/:reviewId/reply
      ・{reply}（1,000文字まで）。上書き可、空の文字列で削除（repliedAt も空に）
      ・初めて返信したときだけ投稿者にサイト内の通知（review_reply。メールなし）
      ・掲載停止中の生産者は 409 PRODUCER_SUSPENDED。他の生産者の商品のレビューは 404 REVIEW_NOT_FOUND
      ・200 で返信したレビュー
"""
from rest_framework.response import Response
from rest_framework.views import APIView

from marche.models import ProductReview

from ...common.pagination import paginate, validate_query
from ...common.permissions import IsApprovedProducer, ensure_producer_not_suspended
from ...serializers.public.reviews import (
    MAX_ID,
    ProducerReviewListQuerySerializer,
    ProducerReviewSerializer,
    ReviewReplySerializer,
)
from ...services.reviews import reply_to_review, review_not_found


class DashboardReviewListView(APIView):
    """GET /api/v1/dashboard/reviews"""

    permission_classes = [IsApprovedProducer]

    def get(self, request):
        query = validate_query(ProducerReviewListQuerySerializer, request)
        reviews = ProductReview.objects.filter(product__producer=request.user.producer)
        if "product_id" in query:
            reviews = reviews.filter(product_id=query["product_id"])
        if query["unreplied"]:
            reviews = reviews.filter(reply__isnull=True)
        items = reviews.select_related("user", "product").order_by("-created_at", "-id")
        return Response(paginate(items, query, ProducerReviewSerializer, count_queryset=reviews))


class DashboardReviewReplyView(APIView):
    """POST /api/v1/dashboard/reviews/:reviewId/reply"""

    permission_classes = [IsApprovedProducer]

    def post(self, request, review_id):
        serializer = ReviewReplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        producer = request.user.producer
        ensure_producer_not_suspended(producer)
        if review_id > MAX_ID:
            raise review_not_found()
        review = reply_to_review(review_id, producer, serializer.validated_data["reply"])
        review = ProductReview.objects.select_related("user", "product").get(pk=review.pk)
        return Response(ProducerReviewSerializer(review).data)
