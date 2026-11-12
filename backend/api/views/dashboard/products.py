"""商品管理（生産者）

認証: 承認済みの生産者（IsApprovedProducer。未ログイン 401、生産者でない・承認前は 403）
仕様: Notion の各API定義＋api-spec.md「7. 実装で決めたこと」。カラム名: claude/er-diagram.md
掲載停止中の生産者: 閲覧だけできる。登録・更新・削除・在庫更新は 409 PRODUCER_SUSPENDED

このファイルの API（シーケンス図は Notion の「生産者の商品管理」）:
    - 商品一覧: GET /api/v1/dashboard/products
        ・自分の商品だけ（すべての公開状態）。publishStatus・categoryId で絞り込み。updated_at・id の降順
    - 商品登録: POST /api/v1/dashboard/products
        ・カテゴリーは実在するもの、配送設定は自分のもの、画像キーは自分がアップロードしたもの（だめなら 400）
        ・公開（public）にするには画像1枚以上・割引後の価格が1円以上（だめなら 400 details.publishStatus）
        ・201 と Location（詳細のURL）。初期値は taxRate=8・真偽値 false・publishStatus=draft・画像なし・stock なし
    - 商品詳細: GET /api/v1/dashboard/products/:productId
    - 商品更新: PATCH /api/v1/dashboard/products/:productId
        ・送った項目だけ変える。stock は受け付けない（在庫更新APIで）。imageKeys を送ったら画像を全部置き換え
        ・結果が public なら公開の条件を確かめる（画像を全部外したときも）
        ・運営に掲載停止された商品は、内容の編集はできるが publishStatus は変えられない（409 CONTENT_SUSPENDED）
    - 商品削除: DELETE /api/v1/dashboard/products/:productId
        ・公開中・掲載停止中・注文されたことがある商品は 409 PRODUCT_DELETE_CONFLICT（非公開にしてもらう）
        ・画像・お気に入り・カートも一緒に消える。204
    - 在庫更新: PATCH /api/v1/dashboard/products/:productId/stock
        ・{stock}（0以上、または null＝在庫管理しない）。{productId, stock, updatedAt} を返す

他の生産者の商品・存在しない ID は 404。同時更新は商品の行をロック（select_for_update）してから確かめる。
"""
from django.db import transaction
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from marche.models import Category, OrderItem, Product, ProductImage, PublishStatus, ShippingSetting

from ...common.exceptions import Conflict
from ...common.pagination import paginate, validate_query
from ...common.permissions import IsApprovedProducer, ensure_producer_not_suspended
from ...common.serializers import QuerySerializer
from ...serializers.dashboard.products import (
    DashboardProductListQuerySerializer,
    DashboardProductSerializer,
    ProductWriteSerializer,
    StockResponseSerializer,
    StockUpdateSerializer,
)
from ...services.storage import validate_image_keys

PLAIN_FIELDS = ["name", "volume", "price", "tax_rate", "discount_rate", "description", "method", "is_subscription",
                "is_preorder", "accepts_delivery_date", "publish_status", "stock"]


def with_images(queryset):
    return queryset.prefetch_related(
        Prefetch("product_images", queryset=ProductImage.objects.order_by("sort_order", "id")))


class ProducerProductView(APIView):
    """商品管理APIの共通部分"""

    permission_classes = [IsApprovedProducer]

    @property
    def producer(self):
        return self.request.user.producer

    def get_product(self, product_id, lock=False):
        """自分の商品を1件取る。他の生産者の商品・存在しない ID は 404"""
        queryset = Product.objects.filter(producer=self.producer)
        if lock:
            queryset = queryset.select_for_update()
        return get_object_or_404(queryset, pk=product_id)

    def respond(self, product, status_code=status.HTTP_200_OK, headers=None):
        """保存後に読み直して返す（sale_price は DB が計算する生成列なので）"""
        product = with_images(Product.objects.filter(pk=product.pk)).get()
        return Response(DashboardProductSerializer(product).data, status=status_code, headers=headers)

    def apply(self, product, data):
        """検証済みの値を product に入れて保存し、画像を置き換える"""
        if "category_id" in data:
            if not Category.objects.filter(pk=data["category_id"]).exists():
                raise serializers.ValidationError({"category_id": ["カテゴリーが見つかりません。"]})
            product.category_id = data["category_id"]
        if "shipping_setting_id" in data:
            # 他の生産者の配送設定かどうかは知らせない（存在しないのと同じ 400）
            if not ShippingSetting.objects.filter(pk=data["shipping_setting_id"], producer=self.producer).exists():
                raise serializers.ValidationError({"shipping_setting_id": ["配送設定が見つかりません。"]})
            product.shipping_setting_id = data["shipping_setting_id"]
        image_keys = data.get("image_keys")
        if image_keys is not None:
            validate_image_keys(self.request.user, image_keys)
        for field in PLAIN_FIELDS:
            if field in data:
                setattr(product, field, data[field])

        image_count = len(image_keys) if image_keys is not None else (
            product.product_images.count() if product.pk else 0)
        ensure_publishable(product, image_count)

        product.save()
        if image_keys is not None:
            ProductImage.objects.filter(product=product).delete()
            ProductImage.objects.bulk_create([
                ProductImage(product=product, image=key, sort_order=order) for order, key in enumerate(image_keys)])


def ensure_publishable(product, image_count):
    """公開（public）にする・公開のまま保存する条件。満たさなければ 400（details.publishStatus）"""
    if product.publish_status != PublishStatus.PUBLIC:
        return
    reasons = []
    if image_count == 0:
        reasons.append("公開するには画像を1枚以上登録してください。")
    sale_price = product.price * (100 - (product.discount_rate or 0)) // 100
    if sale_price < 1:
        reasons.append("公開するには割引後の価格を1円以上にしてください。")
    if reasons:
        raise serializers.ValidationError({"publish_status": reasons})


# =========================================================
# 一覧・登録
# =========================================================

class DashboardProductListCreateView(ProducerProductView):
    """GET・POST /api/v1/dashboard/products"""

    def get(self, request):
        query = validate_query(DashboardProductListQuerySerializer, request)
        products = Product.objects.filter(producer=self.producer)
        if "publish_status" in query:
            products = products.filter(publish_status=query["publish_status"])
        if "category_id" in query:
            products = products.filter(category_id=query["category_id"])
        listed = with_images(products).order_by("-updated_at", "-id")
        return Response(paginate(listed, query, DashboardProductSerializer, count_queryset=products))

    def post(self, request):
        serializer = ProductWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            ensure_producer_not_suspended(self.producer)
            product = Product(producer=self.producer)
            self.apply(product, serializer.validated_data)
        return self.respond(product, status.HTTP_201_CREATED,
                            headers={"Location": f"/api/v1/dashboard/products/{product.pk}"})


# =========================================================
# 詳細・更新・削除
# =========================================================

class DashboardProductDetailView(ProducerProductView):
    """GET・PATCH・DELETE /api/v1/dashboard/products/:productId"""

    def get(self, request, product_id):
        validate_query(QuerySerializer, request)  # クエリパラメーターは受け付けない
        product = get_object_or_404(with_images(Product.objects.filter(producer=self.producer)), pk=product_id)
        return Response(DashboardProductSerializer(product).data)

    def patch(self, request, product_id):
        serializer = ProductWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        with transaction.atomic():
            ensure_producer_not_suspended(self.producer)
            product = self.get_product(product_id, lock=True)
            if product.publish_status == PublishStatus.SUSPENDED and "publish_status" in data:
                raise Conflict("CONTENT_SUSPENDED",
                               "運営により掲載停止中のため、公開状態は変更できません。運営にお問い合わせください。")
            self.apply(product, data)
        return self.respond(product)

    def delete(self, request, product_id):
        with transaction.atomic():
            ensure_producer_not_suspended(self.producer)
            product = self.get_product(product_id, lock=True)
            if product.publish_status in (PublishStatus.PUBLIC, PublishStatus.SUSPENDED):
                raise Conflict("PRODUCT_DELETE_CONFLICT", "公開中・掲載停止中の商品は削除できません。非公開にしてから削除してください。")
            if OrderItem.objects.filter(product=product).exists():
                raise Conflict("PRODUCT_DELETE_CONFLICT", "注文されたことがある商品は削除できません。非公開にしてください。")
            product.delete()  # 画像・お気に入り・カートも一緒に消える（CASCADE）
        return Response(status=status.HTTP_204_NO_CONTENT)


class DashboardProductStockView(ProducerProductView):
    """PATCH /api/v1/dashboard/products/:productId/stock"""

    def patch(self, request, product_id):
        serializer = StockUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            ensure_producer_not_suspended(self.producer)
            product = self.get_product(product_id, lock=True)
            product.stock = serializer.validated_data["stock"]
            product.save(update_fields=["stock", "updated_at"])
        return Response(StockResponseSerializer(product).data)
