"""商品・カテゴリー（公開側） のシリアライザー
商品一覧・商品詳細・カテゴリー一覧のAPIレスポンスを定義するSerializer

使う view: api/views/public/catalog.py
形は Notion の「商品一覧取得API」「商品詳細取得API」「カテゴリー一覧取得API」に合わせる。
Notion から足したもの: isFavorited（一覧・詳細）、craft（詳細）

商品レビュー一覧（GET /api/v1/products/:productId/reviews）はステップ10（レビュー）で書く。
"""
from rest_framework import serializers

from marche.models import Category, Producer, Product, ProductImage, PublishStatus, ShippingSetting

from ...common.images import ImageUrlField
from ...common.pagination import PageQuerySerializer
from ...common.serializers import QueryBooleanField

# BIGINT の上限。これより大きい ID は DB に渡さない（SQLite ではエラーになるため）
MAX_ID = 2 ** 63 - 1

# 並び順。どれも最後に id DESC（並びが毎回変わらないように）
SORT_CHOICES = ["popular", "newest", "price_asc", "price_desc", "rating"]

# 価格帯（割引後の価格 sale_price で判定）
PRICE_CHOICES = ["under2000", "2000to4000", "over4000"]


# =========================================================
# リクエスト（クエリパラメーター）
# =========================================================

class ProductListQuerySerializer(PageQuerySerializer):
    """GET /products の ?q=&categoryId=&producerId=&price=&subscription=&preorder=&sort=&page=&pageSize=

    未知のキー・同じキーの重複・空文字・不正な値は 400（QuerySerializer）
    - q: キーワード（100文字まで）。商品名・生産者名の部分一致
    - price: under2000（2,000円未満）/ 2000to4000（2,000円以上4,000円未満）/ over4000（4,000円以上）
    - subscription・preorder: true は定期便・予約商品だけ、false はそれ以外だけ。省略したら絞り込まない
    """

    category_id = serializers.IntegerField(required=False, min_value=1, max_value=MAX_ID)
    producer_id = serializers.IntegerField(required=False, min_value=1, max_value=MAX_ID)
    q = serializers.CharField(required=False, max_length=100)
    price = serializers.ChoiceField(choices=PRICE_CHOICES, required=False)
    subscription = QueryBooleanField(required=False)
    preorder = QueryBooleanField(required=False)
    sort = serializers.ChoiceField(choices=SORT_CHOICES, required=False, default="popular")


# =========================================================
# レスポンス
# =========================================================

class CategorySerializer(serializers.ModelSerializer):
    """{id, name, sortOrder}"""

    class Meta:
        model = Category
        fields = ["id", "name", "sort_order"]


class ProducerSummarySerializer(serializers.ModelSerializer):
    """{id, businessName, prefectureId, prefectureName, city}"""

    prefecture_name = serializers.CharField(source="prefecture.name")

    class Meta:
        model = Producer
        fields = ["id", "business_name", "prefecture_id", "prefecture_name", "city"]


class ProductSummarySerializer(serializers.ModelSerializer):
    """商品カード1枚分

    view で次の注釈（annotate）を付けた QuerySet を渡す（views/public/catalog.py の annotate_product_list）:
      - thumbnail_key: メイン画像のキー（sort_order・id の昇順で先頭）
      - is_favorited: ログイン中の会員のお気に入りにあるか（未ログインは False）
    stock: null は「在庫管理しない（購入可）」、0 は売り切れ
    """

    thumbnail_url = ImageUrlField(source="thumbnail_key")
    is_favorited = serializers.BooleanField()
    category = CategorySerializer()
    producer = ProducerSummarySerializer()

    class Meta:
        model = Product
        fields = ["id", "name", "volume", "price", "discount_rate", "sale_price", "tax_rate", "rating_avg",
                  "review_count", "stock", "is_subscription", "is_preorder", "thumbnail_url", "is_favorited",
                  "category", "producer"]


class ProductImageSerializer(serializers.ModelSerializer):
    """{id, url, sortOrder}"""

    url = ImageUrlField(source="image")

    class Meta:
        model = ProductImage
        fields = ["id", "url", "sort_order"]


class ShippingSettingSerializer(serializers.ModelSerializer):
    """{temperatureZone, shippingFee, freeShippingThreshold, leadTimeText}。確定送料は注文APIで計算する"""

    class Meta:
        model = ShippingSetting
        fields = ["temperature_zone", "shipping_fee", "free_shipping_threshold", "lead_time_text"]


class ProductDetailSerializer(ProductSummarySerializer):
    """商品詳細 = 商品カードの項目 ＋ 説明・生産方法・画像・配送設定・生産へのこだわり（craft）"""

    images = ProductImageSerializer(source="product_images", many=True)
    shipping = ShippingSettingSerializer(source="shipping_setting")
    method = serializers.SerializerMethodField()
    craft = serializers.SerializerMethodField()

    class Meta(ProductSummarySerializer.Meta):
        fields = ProductSummarySerializer.Meta.fields + [
            "description", "method", "accepts_delivery_date", "images", "shipping", "craft"]

    def get_method(self, product):
        """この商品の生産方法。空なら null（商品詳細に表示しない）"""
        return product.method or None

    def get_craft(self, product):
        """生産者ストーリーの「生産へのこだわり」。ストーリーがない・公開中でない・空なら null"""
        story = getattr(product.producer, "story", None)
        if story is None or story.publish_status != PublishStatus.PUBLIC or not story.craft:
            return None
        return story.craft
