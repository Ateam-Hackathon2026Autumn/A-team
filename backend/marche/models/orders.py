"""カート・注文・返金・商品レビュー"""
from django.conf import settings
from django.db import models
from django.db.models import Q

from .base import TimeStampedModel


class CartItem(TimeStampedModel):
    """カート

    user_id か session_key のどちらか一方が必ず入る（CHECK制約）。ゲストがログインしたら session_key の行を user_id に付け替える。"""

    # 会員のカート。ゲストは空
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="cart_items",
        null=True,
        blank=True,
        verbose_name="会員のカート",
    )

    # ゲストのカート（Djangoのセッションキー）。会員は空
    session_key = models.CharField(
        max_length=40,
        null=True,
        blank=True,
        verbose_name="セッションキー",
    )

    product = models.ForeignKey(
        "marche.Product",
        on_delete=models.CASCADE,
        related_name="cart_items",
        verbose_name="商品",
    )

    # 数量（1〜10）
    quantity = models.IntegerField(
        default=1,
        verbose_name="数量",
    )

    class Meta:
        db_table = "cart_items"
        verbose_name = "カート"
        verbose_name_plural = "カート"
        constraints = [
            models.CheckConstraint(condition=Q(user__isnull=False) | Q(session_key__isnull=False), name="chk_cart_items_user_or_session"),
        ]


class Order(TimeStampedModel):
    """注文

    1回の会計 = 1注文。user_id か guest_email のどちらかが必ず入る（CHECK制約）。注文全体の情報（購入者・お届け先・決済・合計）だけを持ち、発送・キャンセル・返金は order_shipments で管理する。ゲスト注文をあとから会員に引き継ぐことはしない。お届け先は addresses と同じ分け方で値をコピーする。"""

    class PaymentStatus(models.TextChoices):
        PENDING = "pending", "支払い待ち"
        PAID = "paid", "支払い済み"
        FAILED = "failed", "決済失敗・期限切れ"

    # 注文番号（例：TM-20260921-0412）
    order_no = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="注文番号",
    )

    # 購入した会員。ゲスト購入は空
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="orders",
        null=True,
        blank=True,
        verbose_name="購入した会員",
    )

    # ゲストのメールアドレス。注文確認メールの送り先
    guest_email = models.EmailField(
        max_length=254,
        null=True,
        blank=True,
        verbose_name="ゲストのメールアドレス",
    )

    guest_name = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="ゲストの氏名",
    )

    guest_phone = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name="ゲストの電話番号",
    )

    # 閲覧用トークンの SHA-256（16進数）。トークン自体は注文時に secrets.token_urlsafe(32) で作り、確認メールのURLに載せるだけでDBには保存しない。ゲストがログインなしで注文状況を見る・キャンセルするときは、URLのトークンをハッシュ化してこの列で検索する。確認メールの再送時は作り直して上書きする（古いリンクは無効になる）
    access_token_hash = models.CharField(
        max_length=64,
        unique=True,
        verbose_name="閲覧用トークンのハッシュ",
    )

    # お届け先：受取人名（注文時点の写し）
    ship_name = models.CharField(
        max_length=100,
        verbose_name="お届け先：受取人名",
    )

    ship_postal_code = models.CharField(
        max_length=8,
        verbose_name="お届け先：郵便番号",
    )

    # お届け先：都道府県名（文字列で写す）
    ship_prefecture = models.CharField(
        max_length=10,
        verbose_name="お届け先：都道府県名",
    )

    ship_city = models.CharField(
        max_length=50,
        verbose_name="お届け先：市区町村",
    )

    ship_address_line1 = models.CharField(
        max_length=100,
        verbose_name="お届け先：町域・番地",
    )

    ship_address_line2 = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="お届け先：建物名・部屋番号",
    )

    ship_phone = models.CharField(
        max_length=20,
        verbose_name="お届け先：電話番号",
    )

    # card / konbini など
    payment_method = models.CharField(
        max_length=20,
        verbose_name="支払い方法",
    )

    # 商品小計（割引後・税込・円）。注文時点の値で、キャンセルされても書き換えない
    items_total = models.IntegerField(
        verbose_name="商品小計",
    )

    # 送料合計（order_shipments.shipping_fee の合計・円）
    shipping_total = models.IntegerField(
        default=0,
        verbose_name="送料合計",
    )

    # 合計・税込（円）
    grand_total = models.IntegerField(
        verbose_name="合計・税込",
    )

    # 8%対象分の消費税額（円）
    tax_8_amount = models.IntegerField(
        default=0,
        verbose_name="8%対象分の消費税額",
    )

    # 10%対象分の消費税額（円）。送料を含む
    tax_10_amount = models.IntegerField(
        default=0,
        verbose_name="10%対象分の消費税額",
    )

    # pending（支払い待ち）/ paid（支払い済み）/ failed（決済失敗・期限切れ）
    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        verbose_name="決済状態",
    )

    # Stripe の決済ID
    stripe_payment_intent_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Stripe 決済ID",
    )

    ordered_at = models.DateTimeField(
        verbose_name="注文日時",
    )

    class Meta:
        db_table = "orders"
        verbose_name = "注文"
        verbose_name_plural = "注文"
        constraints = [
            models.CheckConstraint(condition=Q(user__isnull=False) | Q(guest_email__isnull=False), name="chk_orders_user_or_guest"),
        ]

    def __str__(self):
        return self.order_no


class OrderShipment(TimeStampedModel):
    """発送（生産者×温度帯）

    1注文を「生産者×温度帯」の箱に分ける（order_id + producer_id + temperature_zone でユニーク）。送料は箱ごとにかかる。キャンセルは生産者単位で受け付け、その生産者の箱をまとめて canceled にして、箱ごとに返金する。生産者の注文管理はこの単位で見る。"""

    class TemperatureZone(models.TextChoices):
        NORMAL = "normal", "常温"
        CHILLED = "chilled", "冷蔵"
        FROZEN = "frozen", "冷凍"

    class Status(models.TextChoices):
        UNSHIPPED = "unshipped", "未発送"
        SHIPPED = "shipped", "発送済み"
        DELIVERED = "delivered", "配達完了"
        CANCEL_REQUESTED = "cancel_requested", "キャンセル申請中"
        CANCELED = "canceled", "キャンセル済み"

    order = models.ForeignKey(
        "marche.Order",
        on_delete=models.CASCADE,
        related_name="order_shipments",
        verbose_name="注文",
    )

    producer = models.ForeignKey(
        "marche.Producer",
        on_delete=models.PROTECT,
        related_name="order_shipments",
        verbose_name="発送する生産者",
    )

    # normal（常温）/ chilled（冷蔵）/ frozen（冷凍）。温度帯が違えば別の箱で送る
    temperature_zone = models.CharField(
        max_length=20,
        choices=TemperatureZone.choices,
        verbose_name="温度帯",
    )

    # この箱の送料（円・注文時点）。shipping_settings の送料を写す。商品の合計が free_shipping_threshold 以上なら0
    shipping_fee = models.IntegerField(
        verbose_name="この箱の送料",
    )

    desired_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="お届け希望日",
    )

    desired_time = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name="お届け希望時間帯",
    )

    # unshipped（未発送）/ shipped（発送済み）/ delivered（配達完了）/ cancel_requested（キャンセル申請中）/ canceled（キャンセル済み）
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.UNSHIPPED,
        verbose_name="発送状態",
    )

    tracking_no = models.CharField(
        max_length=30,
        null=True,
        blank=True,
        verbose_name="送り状番号",
    )

    shipped_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="発送日時",
    )

    cancel_reason = models.TextField(
        null=True,
        blank=True,
        verbose_name="キャンセル申請の理由",
    )

    canceled_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="キャンセルが確定した日時",
    )

    # 返金額（円）。この箱の明細の subtotal の合計＋shipping_fee。返金するまでは空
    refunded_amount = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="返金額",
    )

    # Stripe の返金ID（箱ごとに部分返金する）
    stripe_refund_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Stripe 返金ID",
    )

    class Meta:
        db_table = "order_shipments"
        verbose_name = "発送（生産者×温度帯）"
        verbose_name_plural = "発送（生産者×温度帯）"
        constraints = [
            models.UniqueConstraint(fields=['order', 'producer', 'temperature_zone'], name="uniq_order_shipments_order_producer_temperature_zone"),
        ]


class OrderItem(TimeStampedModel):
    """注文明細

    注文時点の価格と割引率を写して持つ。あとで商品の割引率や価格が変わっても、注文金額と返金額は変わらない。"""

    # 発送（箱）
    shipment = models.ForeignKey(
        "marche.OrderShipment",
        on_delete=models.CASCADE,
        related_name="order_items",
        verbose_name="発送",
    )

    product = models.ForeignKey(
        "marche.Product",
        on_delete=models.PROTECT,
        related_name="order_items",
        verbose_name="商品",
    )

    product_name = models.CharField(
        max_length=100,
        verbose_name="注文時点の商品名",
    )

    # 注文時点の定価・税込（円）
    unit_price = models.IntegerField(
        verbose_name="注文時点の定価・税込",
    )

    # 注文時点の割引率（%）。1〜99（CHECK制約）。空は割引なし
    discount_rate = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name="注文時点の割引率",
    )

    # 割引後の単価・税込（円・端数切り捨て）
    paid_unit_price = models.IntegerField(
        verbose_name="割引後の単価・税込",
    )

    quantity = models.IntegerField(
        default=1,
        verbose_name="数量",
    )

    # 注文時点の消費税率（%）
    tax_rate = models.PositiveSmallIntegerField(
        default=8,
        verbose_name="注文時点の消費税率",
    )

    # 小計＝paid_unit_price × quantity（税込・円）
    subtotal = models.IntegerField(
        verbose_name="小計＝paid_unit_price × quantity",
    )

    class Meta:
        db_table = "order_items"
        verbose_name = "注文明細"
        verbose_name_plural = "注文明細"
        constraints = [
            models.CheckConstraint(condition=Q(discount_rate__isnull=True) | Q(discount_rate__gte=1, discount_rate__lte=99), name="chk_order_items_discount_rate"),
        ]


class ProductReview(TimeStampedModel):
    """商品レビュー

    登録・編集・削除のたびに、同じトランザクションで products.rating_avg / review_count をこの商品の分だけ集計し直す。集計用に複合インデックス (product_id, rating) を張る。"""

    # 購入した明細。1明細につき1件
    order_item = models.OneToOneField(
        "marche.OrderItem",
        on_delete=models.PROTECT,
        related_name="review",
        verbose_name="購入した明細",
    )

    # 商品（集計用）
    product = models.ForeignKey(
        "marche.Product",
        on_delete=models.PROTECT,
        related_name="product_reviews",
        verbose_name="商品",
    )

    # 書いた会員。レビューは会員のみ
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="product_reviews",
        verbose_name="書いた会員",
    )

    # 評価（1〜5）
    rating = models.PositiveSmallIntegerField(
        verbose_name="評価",
    )

    body = models.TextField(
        null=True,
        blank=True,
        verbose_name="本文",
    )

    reply = models.TextField(
        null=True,
        blank=True,
        verbose_name="生産者の返信",
    )

    replied_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="返信日時",
    )

    class Meta:
        db_table = "product_reviews"
        verbose_name = "商品レビュー"
        verbose_name_plural = "商品レビュー"
        indexes = [
            models.Index(fields=['product', 'rating'], name="idx_product_reviews_rating"),
        ]
