"""生産者・申請・学ぶページ"""
from django.conf import settings
from django.db import models

from .base import PublishStatus, TimeStampedModel


class Producer(TimeStampedModel):
    """生産者

    users にぶら下がる生産者プロフィール。バッジは列で持たず、career_start_year / approved_at / accepts_experience / recruiting から表示時に判定する。"""

    class Genre(models.TextChoices):
        AGRICULTURE = "agriculture", "農業"
        LIVESTOCK = "livestock", "畜産"
        FISHERY = "fishery", "漁業"

    class ApprovalStatus(models.TextChoices):
        PENDING = "pending", "審査待ち"
        APPROVED = "approved", "承認"
        REJECTED = "rejected", "却下"
        RETURNED = "returned", "差し戻し"

    # ログインアカウント。1ユーザーにつき1生産者
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="producer",
        verbose_name="ログインアカウント",
    )

    # 事業者名（農園・漁協・牧場などの名前）
    business_name = models.CharField(
        max_length=100,
        verbose_name="事業者名",
    )

    representative_name = models.CharField(
        max_length=100,
        verbose_name="代表者名",
    )

    # agriculture（農業）/ livestock（畜産）/ fishery（漁業）
    genre = models.CharField(
        max_length=20,
        choices=Genre.choices,
        verbose_name="業種",
    )

    # 所在地の都道府県。エリア検索に使う
    prefecture = models.ForeignKey(
        "marche.Prefecture",
        on_delete=models.PROTECT,
        related_name="producers",
        verbose_name="所在地の都道府県",
    )

    # 市区町村。公開するのはここまで（番地は持たない）
    city = models.CharField(
        max_length=50,
        verbose_name="市区町村",
    )

    # 生産品目（例：りんご・ぶどう）
    production_items = models.CharField(
        max_length=100,
        verbose_name="生産品目",
    )

    intro = models.TextField(
        verbose_name="ひとこと紹介",
    )

    # 本人がこの仕事を始めた年。5年以内なら新規就業バッジ（表示は genre で「新規就農」「新規就漁」などに出し分け）
    career_start_year = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name="この仕事を始めた年",
    )

    # 事業の創業年（例：三代目の農園なら1962）。本人が始めた年は career_start_year。表示用
    founded_year = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name="事業の創業年",
    )

    accepts_experience = models.BooleanField(
        default=False,
        verbose_name="体験受け入れ中バッジ",
    )

    recruiting = models.BooleanField(
        default=False,
        verbose_name="担い手募集中バッジ",
    )

    # プロフィール画像（S3のキー）
    profile_image = models.ImageField(
        upload_to="producers/",
        max_length=500,
        null=True,
        blank=True,
        verbose_name="プロフィール画像",
    )

    # 農園のメイン画像（S3のキー）
    cover_image = models.ImageField(
        upload_to="producers/",
        max_length=500,
        null=True,
        blank=True,
        verbose_name="農園のメイン画像",
    )

    # pending（審査待ち）/ approved / rejected / returned（差し戻し）
    approval_status = models.CharField(
        max_length=20,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING,
        verbose_name="審査状態",
    )

    # 承認日時。新規参加バッジの判定に使う
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="承認日時",
    )

    # draft（下書き）/ public（公開）/ private（非公開）/ suspended（運営による掲載停止）
    publish_status = models.CharField(
        max_length=20,
        choices=PublishStatus.choices,
        default=PublishStatus.DRAFT,
        verbose_name="公開状態",
    )

    # 注目スコア。夜間バッチで更新（初期値0）
    featured_score = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        verbose_name="注目スコア",
    )

    # Stripe Connect の売上受取アカウント（拡張）
    stripe_account_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Stripe 売上受取アカウントID",
    )

    class Meta:
        db_table = "producers"
        verbose_name = "生産者"
        verbose_name_plural = "生産者"

    def __str__(self):
        return self.business_name


class ProducerImage(TimeStampedModel):
    """農園画像"""

    producer = models.ForeignKey(
        "marche.Producer",
        on_delete=models.CASCADE,
        related_name="producer_images",
        verbose_name="生産者",
    )

    # 画像（S3のキー）
    image = models.ImageField(
        upload_to="producer_images/",
        max_length=500,
        verbose_name="画像",
    )

    sort_order = models.IntegerField(
        default=0,
        verbose_name="表示順",
    )

    class Meta:
        db_table = "producer_images"
        verbose_name = "農園画像"
        verbose_name_plural = "農園画像"
        ordering = ["sort_order", "id"]


class ShippingSetting(TimeStampedModel):
    """配送設定

    生産者×温度帯で1行。producer_id + temperature_zone でユニーク。"""

    class TemperatureZone(models.TextChoices):
        NORMAL = "normal", "常温"
        CHILLED = "chilled", "冷蔵"
        FROZEN = "frozen", "冷凍"

    producer = models.ForeignKey(
        "marche.Producer",
        on_delete=models.CASCADE,
        related_name="shipping_settings",
        verbose_name="生産者",
    )

    # normal（常温）/ chilled（冷蔵）/ frozen（冷凍）
    temperature_zone = models.CharField(
        max_length=20,
        choices=TemperatureZone.choices,
        verbose_name="温度帯",
    )

    # 送料（円）
    shipping_fee = models.IntegerField(
        verbose_name="送料",
    )

    # この金額以上で送料無料（円）。同じ温度帯の箱の商品合計（割引後）で判定する。空なら送料無料にしない。送料無料は商品ごとではなくこのルールだけで決める
    free_shipping_threshold = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="送料無料になる金額",
    )

    # 発送目安（例：2〜4日で発送）
    lead_time_text = models.CharField(
        max_length=50,
        verbose_name="発送目安",
    )

    class Meta:
        db_table = "shipping_settings"
        verbose_name = "配送設定"
        verbose_name_plural = "配送設定"
        constraints = [
            models.UniqueConstraint(fields=['producer', 'temperature_zone'], name="uniq_shipping_settings_producer_temperature_zone"),
        ]


class ProducerApplication(TimeStampedModel):
    """生産者申請

    差し戻し後の再申請は新しい行を追加し、審査の履歴を残す。"""

    class Status(models.TextChoices):
        PENDING = "pending", "審査待ち"
        APPROVED = "approved", "承認"
        REJECTED = "rejected", "却下"
        RETURNED = "returned", "差し戻し"

    producer = models.ForeignKey(
        "marche.Producer",
        on_delete=models.CASCADE,
        related_name="producer_applications",
        verbose_name="申請した生産者",
    )

    # pending / approved / rejected / returned
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="審査状態",
    )

    application_reason = models.TextField(
        verbose_name="申請理由・自己紹介",
    )

    # 審査した運営スタッフ。審査前は空
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="producer_applications",
        null=True,
        blank=True,
        verbose_name="審査した運営スタッフ",
    )

    review_comment = models.TextField(
        null=True,
        blank=True,
        verbose_name="却下・差し戻しの理由",
    )

    submitted_at = models.DateTimeField(
        verbose_name="申請日時",
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="審査日時",
    )

    class Meta:
        db_table = "producer_applications"
        verbose_name = "生産者申請"
        verbose_name_plural = "生産者申請"


class ApplicationDocument(TimeStampedModel):
    """申請書類"""

    class CheckStatus(models.TextChoices):
        UNCHECKED = "unchecked", "未確認"
        OK = "ok", "問題なし"
        NG = "ng", "不備あり"

    application = models.ForeignKey(
        "marche.ProducerApplication",
        on_delete=models.CASCADE,
        related_name="application_documents",
        verbose_name="申請",
    )

    # 本人確認 / 営業許可 / 農地・漁業権 など
    doc_type = models.CharField(
        max_length=30,
        verbose_name="書類の種類",
    )

    # ファイル（S3のキー）
    file = models.FileField(
        upload_to="application_documents/",
        max_length=500,
        verbose_name="ファイル",
    )

    # unchecked / ok / ng
    check_status = models.CharField(
        max_length=20,
        choices=CheckStatus.choices,
        default=CheckStatus.UNCHECKED,
        verbose_name="確認状態",
    )

    class Meta:
        db_table = "application_documents"
        verbose_name = "申請書類"
        verbose_name_plural = "申請書類"


class ProducerStory(TimeStampedModel):
    """生産者ストーリー

    学ぶページの内容。決まった項目を1つずつ埋める入力フォームにする。生産者の登録時に空の行を作り、書ける項目から埋めてもらう。生産者ページの応援ブロックもここから取る。"""

    # 生産者。1生産者につき1行
    producer = models.OneToOneField(
        "marche.Producer",
        on_delete=models.CASCADE,
        related_name="story",
        verbose_name="生産者",
    )

    # 生産へのこだわり（生産理念）。生産者ページ・商品詳細にも表示
    craft = models.TextField(
        null=True,
        blank=True,
        verbose_name="生産へのこだわり",
    )

    method = models.TextField(
        null=True,
        blank=True,
        verbose_name="栽培・飼育・漁業の方法",
    )

    # 商品ができるまで（生産工程）
    process = models.TextField(
        null=True,
        blank=True,
        verbose_name="商品ができるまで",
    )

    environment = models.TextField(
        null=True,
        blank=True,
        verbose_name="環境への取り組み",
    )

    # この仕事を始めた理由（応援ブロック）
    reason = models.TextField(
        null=True,
        blank=True,
        verbose_name="この仕事を始めた理由",
    )

    # これからの目標（応援ブロック）
    goal = models.TextField(
        null=True,
        blank=True,
        verbose_name="これからの目標",
    )

    # draft（下書き）/ public（公開）/ private（非公開）/ suspended（運営による掲載停止）。問題のある内容を運営が非公開にできる
    publish_status = models.CharField(
        max_length=20,
        choices=PublishStatus.choices,
        default=PublishStatus.DRAFT,
        verbose_name="公開状態",
    )

    class Meta:
        db_table = "producer_stories"
        verbose_name = "生産者ストーリー"
        verbose_name_plural = "生産者ストーリー"
