"""商品管理（生産者） のシリアライザー

使う view: api/views/dashboard/products.py
形は Notion の「商品一覧取得API」「商品登録API」「商品詳細取得API」「商品更新API」「在庫更新API」に合わせる。
Notion から変えたもの（api-spec「7. 実装で決めたこと」）:
  - etag・If-Match は使わない
  - stock の null は「在庫管理しない（購入できる）」。公開中でも null にできる
  - 公開の条件は「画像1枚以上・割引後の価格が1円以上」。満たさないときは 400（details.publishStatus）
"""
from rest_framework import serializers

from marche.models import Product, ProductImage, PublishStatus

from ...common.images import ImageUrlField
from ...common.pagination import PageQuerySerializer
from ...common.serializers import StrictSerializer

MAX_INT = 2 ** 31 - 1
MAX_ID = 2 ** 63 - 1
MAX_IMAGES = 10
PRODUCER_PUBLISH_CHOICES = [PublishStatus.DRAFT, PublishStatus.PUBLIC, PublishStatus.PRIVATE]


# =========================================================
# リクエスト
# =========================================================

class DashboardProductListQuerySerializer(PageQuerySerializer):
    """GET /dashboard/products の ?publishStatus=&categoryId=&page=&pageSize=（省略時は全状態・全カテゴリー）"""

    publish_status = serializers.ChoiceField(choices=PublishStatus.choices, required=False)
    category_id = serializers.IntegerField(required=False, min_value=1, max_value=MAX_INT)


class ProductWriteSerializer(StrictSerializer):
    """POST（登録）と PATCH（更新）の本文。更新は partial=True で使う

    - 文字列は前後の空白を除く。必須の文字列は空・null 不可
    - imageKeys: 最大10件・重複不可。配列の順が sort_order（0がメイン）。指定したら全部置き換え（[] で画像なし）
    - stock: 登録のときだけ受け付ける（更新は在庫更新APIで）
    - category・配送設定・画像キーの存在と持ち主は view で確かめる
    """

    name = serializers.CharField(max_length=100)
    volume = serializers.CharField(max_length=50)
    category_id = serializers.IntegerField(min_value=1, max_value=MAX_INT)
    shipping_setting_id = serializers.IntegerField(min_value=1, max_value=MAX_ID)
    price = serializers.IntegerField(min_value=1, max_value=MAX_INT)
    tax_rate = serializers.ChoiceField(choices=[8, 10], required=False)
    discount_rate = serializers.IntegerField(min_value=1, max_value=99, required=False, allow_null=True)
    description = serializers.CharField()
    method = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    is_subscription = serializers.BooleanField(required=False)
    is_preorder = serializers.BooleanField(required=False)
    accepts_delivery_date = serializers.BooleanField(required=False)
    publish_status = serializers.ChoiceField(choices=PRODUCER_PUBLISH_CHOICES, required=False)
    image_keys = serializers.ListField(child=serializers.CharField(max_length=500), max_length=MAX_IMAGES,
                                       required=False)
    stock = serializers.IntegerField(min_value=0, max_value=MAX_INT, required=False, allow_null=True)

    def validate_image_keys(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError("同じ画像を複数指定することはできません。")
        return value

    def validate_method(self, value):
        return value or None  # 空なら null（商品詳細に表示しない）

    def validate(self, attrs):
        if self.partial:
            if not attrs:
                raise serializers.ValidationError({"non_field_errors": ["変更する項目を指定してください。"]})
            if "stock" in attrs:
                raise serializers.ValidationError({"stock": ["在庫は在庫更新APIで変更してください。"]})
        return attrs


class StockUpdateSerializer(StrictSerializer):
    """PATCH /dashboard/products/:productId/stock の本文 {stock}。在庫数を絶対値で設定。null は在庫管理しない"""

    stock = serializers.IntegerField(min_value=0, max_value=MAX_INT, allow_null=True)


# =========================================================
# レスポンス
# =========================================================

class DashboardProductImageSerializer(serializers.ModelSerializer):
    """{id, key, url, sortOrder}（key は更新APIの imageKeys にそのまま送れる）"""

    key = serializers.CharField(source="image.name")
    url = ImageUrlField(source="image")

    class Meta:
        model = ProductImage
        fields = ["id", "key", "url", "sort_order"]


class DashboardProductSerializer(serializers.ModelSerializer):
    """商品（一覧の1件・詳細・登録と更新のレスポンス）。画像は product_images を prefetch しておく"""

    images = DashboardProductImageSerializer(source="product_images", many=True)

    class Meta:
        model = Product
        fields = ["id", "producer_id", "name", "volume", "category_id", "shipping_setting_id", "price", "tax_rate",
                  "discount_rate", "description", "method", "is_subscription", "is_preorder", "accepts_delivery_date",
                  "publish_status", "sale_price", "stock", "rating_avg", "review_count", "images", "created_at",
                  "updated_at"]


class StockResponseSerializer(serializers.ModelSerializer):
    """在庫更新のレスポンス {productId, stock, updatedAt}"""

    product_id = serializers.IntegerField(source="id")

    class Meta:
        model = Product
        fields = ["product_id", "stock", "updated_at"]
