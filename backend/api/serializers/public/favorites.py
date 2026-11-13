"""お気に入り（生産者フォローを兼ねる） のシリアライザー

使う view: api/views/public/favorites.py
Notion には名前だけで定義がないので、形は api-spec.md と「7. 実装で決めたこと」で決めた。
- 一覧の1件: 商品 {product, isPublic, favoritedAt} / 生産者 {producer, isPublic, notify, favoritedAt}
  product・producer は商品一覧・生産者一覧の1件と同じ形（非公開になったものも残し、isPublic で見分ける）
"""
from rest_framework import serializers

from marche.models import FavoriteProducer, FavoriteProduct

from ...common.pagination import PageQuerySerializer
from ...common.serializers import StrictSerializer
from .catalog import ProductSummarySerializer
from .producers import PublicProducerSerializer


# =========================================================
# リクエスト
# =========================================================

class FavoriteListQuerySerializer(PageQuerySerializer):
    """GET /users/me/favorites の ?type=&page=&pageSize=（type は必須）"""

    type = serializers.ChoiceField(choices=["product", "producer"])


class FavoriteProducerBodySerializer(StrictSerializer):
    """PUT /users/me/favorites/producers/:producerId の本文 {notify}（省略可）"""

    notify = serializers.BooleanField(required=False)


# =========================================================
# レスポンス
# =========================================================

class FavoriteProductItemSerializer(serializers.ModelSerializer):
    """view で thumbnail_key・is_public を注釈した FavoriteProduct を渡す"""

    product = serializers.SerializerMethodField()
    is_public = serializers.BooleanField()
    favorited_at = serializers.DateTimeField(source="created_at")

    class Meta:
        model = FavoriteProduct
        fields = ["product", "is_public", "favorited_at"]

    def get_product(self, favorite):
        product = favorite.product
        product.thumbnail_key = favorite.thumbnail_key
        product.is_favorited = True
        return ProductSummarySerializer(product).data


class FavoriteProducerItemSerializer(serializers.ModelSerializer):
    """view で has_public_story・is_public を注釈した FavoriteProducer を渡す（context に now）"""

    producer = serializers.SerializerMethodField()
    is_public = serializers.BooleanField()
    favorited_at = serializers.DateTimeField(source="created_at")

    class Meta:
        model = FavoriteProducer
        fields = ["producer", "is_public", "notify", "favorited_at"]

    def get_producer(self, favorite):
        producer = favorite.producer
        producer.has_public_story = favorite.has_public_story
        producer.is_favorited = True
        return PublicProducerSerializer(producer, context=self.context).data
