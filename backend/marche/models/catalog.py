"""商品・カテゴリー・お気に入り"""
from django.conf import settings
from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Coalesce, Floor

from .base import PublishStatus, TimeStampedModel


class Category(models.Model):
    """商品カテゴリー"""

    id = models.AutoField(
        primary_key=True,
    )

    # 野菜 / 果物 / 米 / お茶 / 魚介類 / 肉 など
    name = models.CharField(
        max_length=30,
        unique=True,
        verbose_name="カテゴリー名",
    )

    sort_order = models.IntegerField(
        default=0,
        verbose_name="表示順",
    )

    class Meta:
        db_table = "categories"
        verbose_name = "商品カテゴリー"
        verbose_name_plural = "商品カテゴリー"
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.name


class Product(TimeStampedModel):
    """商品

    一覧の並び順（新着・価格の安い順／高い順・人気・評価）に合わせ、複合インデックス (publish_status, created_at) / (publish_status, sale_price) / (publish_status, popularity_score) / (publish_status, rating_avg) を張る。どの並び順も最後に id DESC を付ける。"""

    producer = models.ForeignKey(
        "marche.Producer",
        on_delete=models.PROTECT,
        related_name="products",
        verbose_name="出品した生産者",
    )

    category = models.ForeignKey(
        "marche.Category",
        on_delete=models.PROTECT,
        related_name="products",
        verbose_name="カテゴリー",
    )

    # 送るときの温度帯
    shipping_setting = models.ForeignKey(
        "marche.ShippingSetting",
        on_delete=models.PROTECT,
        related_name="products",
        verbose_name="配送設定",
    )

    name = models.CharField(
        max_length=100,
        verbose_name="商品名",
    )

    # 内容量（例：5kg 14〜18玉）
    volume = models.CharField(
        max_length=50,
        verbose_name="内容量",
    )

    description = models.TextField(
        verbose_name="商品説明",
    )

    # この商品の生産方法（品種・栽培や加工の手順など）。空なら商品詳細に表示しない
    method = models.TextField(
        null=True,
        blank=True,
        verbose_name="この商品の生産方法",
    )

    # 定価・税込（円）
    price = models.IntegerField(
        verbose_name="定価・税込",
    )

    # 消費税率（%）。8＝食品（軽減税率）／10＝酒類・花・苗など。初期値8
    tax_rate = models.PositiveSmallIntegerField(
        default=8,
        verbose_name="消費税率",
    )

    # 割引率（%）。1〜99（CHECK制約）。空は割引なし。期間は持たず、生産者が消せば割引なしに戻る
    discount_rate = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name="割引率",
    )

    # 割引後の価格・税込（円）。MySQLの生成列（STORED）：price * (100 - IFNULL(discount_rate, 0)) DIV 100（端数切り捨て）。DBが自動で計算するのでアプリからは書き込まない。価格順の並び替えに使う
    sale_price = models.GeneratedField(
        expression=Floor(F("price") * (100 - Coalesce(F("discount_rate"), 0, output_field=models.IntegerField())) / 100),
        output_field=models.IntegerField(),
        db_persist=True,
        verbose_name="割引後の価格",
    )

    # 人気スコア。直近の販売数・お気に入り数などから夜間バッチで計算する（初期値0）
    popularity_score = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        verbose_name="人気スコア",
    )

    # 平均評価（1.0〜5.0）。レビューがなければ空。レビューの登録・編集・削除のたびに、この商品の product_reviews を集計し直して保存する
    rating_avg = models.DecimalField(
        max_digits=2,
        decimal_places=1,
        null=True,
        blank=True,
        verbose_name="平均評価",
    )

    # レビュー件数（初期値0）。rating_avg と同時に更新する
    review_count = models.IntegerField(
        default=0,
        verbose_name="レビュー件数",
    )

    # 在庫数。空なら在庫管理しない（在庫管理は拡張）
    stock = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="在庫数",
    )

    is_subscription = models.BooleanField(
        default=False,
        verbose_name="定期便",
    )

    is_preorder = models.BooleanField(
        default=False,
        verbose_name="予約商品",
    )

    accepts_delivery_date = models.BooleanField(
        default=False,
        verbose_name="お届け日時の指定ができる",
    )

    # draft（下書き）/ public（公開）/ private（非公開）/ suspended（運営による掲載停止）
    publish_status = models.CharField(
        max_length=20,
        choices=PublishStatus.choices,
        default=PublishStatus.DRAFT,
        verbose_name="公開状態",
    )

    class Meta:
        db_table = "products"
        verbose_name = "商品"
        verbose_name_plural = "商品"
        indexes = [
            models.Index(fields=['publish_status', 'created_at'], name="idx_products_pub_created"),
            models.Index(fields=['publish_status', 'sale_price'], name="idx_products_pub_sale_price"),
            models.Index(fields=['publish_status', 'popularity_score'], name="idx_products_pub_popularity"),
            models.Index(fields=['publish_status', 'rating_avg'], name="idx_products_pub_rating"),
        ]
        constraints = [
            models.CheckConstraint(condition=Q(discount_rate__isnull=True) | Q(discount_rate__gte=1, discount_rate__lte=99), name="chk_products_discount_rate"),
        ]

    def __str__(self):
        return self.name


class ProductImage(TimeStampedModel):
    """商品画像"""

    product = models.ForeignKey(
        "marche.Product",
        on_delete=models.CASCADE,
        related_name="product_images",
        verbose_name="商品",
    )

    # 画像（S3のキー）
    image = models.ImageField(
        upload_to="product_images/",
        max_length=500,
        verbose_name="画像",
    )

    # 表示順。0がメイン
    sort_order = models.IntegerField(
        default=0,
        verbose_name="表示順",
    )

    class Meta:
        db_table = "product_images"
        verbose_name = "商品画像"
        verbose_name_plural = "商品画像"
        ordering = ["sort_order", "id"]


class FavoriteProduct(TimeStampedModel):
    """お気に入り商品

    user_id + product_id でユニーク。"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="favorite_products",
        verbose_name="会員",
    )

    product = models.ForeignKey(
        "marche.Product",
        on_delete=models.CASCADE,
        related_name="favorite_products",
        verbose_name="商品",
    )

    class Meta:
        db_table = "favorite_products"
        verbose_name = "お気に入り商品"
        verbose_name_plural = "お気に入り商品"
        constraints = [
            models.UniqueConstraint(fields=['user', 'product'], name="uniq_favorite_products_user_product"),
        ]


class FavoriteProducer(TimeStampedModel):
    """お気に入り生産者

    user_id + producer_id でユニーク。生産者フォロー（拡張）もこのテーブルで兼ねる。"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="favorite_producers",
        verbose_name="会員",
    )

    producer = models.ForeignKey(
        "marche.Producer",
        on_delete=models.CASCADE,
        related_name="favorite_producers",
        verbose_name="生産者",
    )

    # 新着お知らせをメールで受け取る（拡張）。お気に入り登録時に本人が選ぶ。初期値 False（配信の同意を本人から取るため）。notification_settings.email_favorite もオンのときだけ送る
    notify = models.BooleanField(
        default=False,
        verbose_name="新着お知らせをメールで受け取る",
    )

    class Meta:
        db_table = "favorite_producers"
        verbose_name = "お気に入り生産者"
        verbose_name_plural = "お気に入り生産者"
        constraints = [
            models.UniqueConstraint(fields=['user', 'producer'], name="uniq_favorite_producers_user_producer"),
        ]
