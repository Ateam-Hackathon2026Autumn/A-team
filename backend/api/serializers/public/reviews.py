"""商品レビュー のシリアライザー（公開側・投稿者・生産者で共通）

使う view: api/views/public/reviews.py、api/views/dashboard/reviews.py

実装済み:
  - ReviewSerializer: レビュー1件 {id, rating, body, reviewerName, reply, repliedAt, createdAt, updatedAt}
      reviewerName は投稿者の名（first_name）だけ。退会した人は「退会ユーザー」。user を select_related しておく
  - ProducerReviewSerializer: 生産者の一覧の1件（上に product: {id, name} を足す）
  - ReviewCreateSerializer: 投稿の本文 {rating（1〜5）, body（任意・1,000文字まで、空なら null）, orderItemId（任意）}
  - ReviewUpdateSerializer: 編集の本文（rating・body のうち送った項目だけ。空のオブジェクトは400）
  - ReviewReplySerializer: 生産者の返信の本文 {reply}（1,000文字まで。空の文字列で返信を消す）
  - ProducerReviewListQuerySerializer: 生産者の一覧のクエリ（page・pageSize・productId・unreplied）

入力エラーは 400（項目ごとのメッセージ）。カラム名は claude/er-diagram.md に合わせる
"""
from rest_framework import serializers

from marche.models import ProductReview

from ...common.pagination import PageQuerySerializer
from ...common.serializers import QueryBooleanField, StrictSerializer

MAX_ID = 2 ** 63 - 1
BODY_MAX = 1000
DELETED_NAME = "退会ユーザー"


class ReviewSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.SerializerMethodField()

    class Meta:
        model = ProductReview
        fields = ["id", "rating", "body", "reviewer_name", "reply", "replied_at", "created_at", "updated_at"]

    def get_reviewer_name(self, review):
        return DELETED_NAME if review.user.deleted_at else review.user.first_name


class ReviewProductSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()


class ProducerReviewSerializer(ReviewSerializer):
    product = ReviewProductSerializer()

    class Meta(ReviewSerializer.Meta):
        fields = ReviewSerializer.Meta.fields + ["product"]


class ReviewCreateSerializer(StrictSerializer):
    rating = serializers.IntegerField(min_value=1, max_value=5)
    body = serializers.CharField(max_length=BODY_MAX, required=False, allow_null=True, allow_blank=True)
    order_item_id = serializers.IntegerField(min_value=1, max_value=MAX_ID, required=False)

    def validate_body(self, value):
        return value or None


class ReviewUpdateSerializer(StrictSerializer):
    rating = serializers.IntegerField(min_value=1, max_value=5, required=False)
    body = serializers.CharField(max_length=BODY_MAX, required=False, allow_null=True, allow_blank=True)

    def validate_body(self, value):
        return value or None

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError({"non_field_errors": ["変更する項目を指定してください。"]})
        return attrs


class ReviewReplySerializer(StrictSerializer):
    reply = serializers.CharField(max_length=BODY_MAX, allow_blank=True)


class ProducerReviewListQuerySerializer(PageQuerySerializer):
    product_id = serializers.IntegerField(required=False, min_value=1, max_value=MAX_ID)
    unreplied = QueryBooleanField(required=False, default=False)
