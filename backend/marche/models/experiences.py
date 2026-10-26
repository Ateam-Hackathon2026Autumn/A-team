"""体験プログラム・日程・予約"""
from django.conf import settings
from django.db import models

from .base import PublishStatus, TimeStampedModel


class Experience(TimeStampedModel):
    """体験プログラム

    流れ・持ち物・注意事項は検索に使わないので JSON にまとめた。メイン画像は experience_images の sort_order = 0（商品と同じ扱い）。エリアは prefecture_id → prefectures → areas でたどる。"""

    producer = models.ForeignKey(
        "marche.Producer",
        on_delete=models.PROTECT,
        related_name="experiences",
        verbose_name="主催する生産者",
    )

    # 開催地の都道府県。エリア検索に使う。登録時は生産者の都道府県を初期値にする
    prefecture = models.ForeignKey(
        "marche.Prefecture",
        on_delete=models.PROTECT,
        related_name="experiences",
        verbose_name="開催地の都道府県",
    )

    title = models.CharField(
        max_length=100,
        verbose_name="タイトル",
    )

    description = models.TextField(
        verbose_name="体験内容",
    )

    # 開催場所・集合場所（市区町村以下の詳しい場所）
    place = models.CharField(
        max_length=200,
        verbose_name="開催場所・集合場所",
    )

    # 大人1名の料金（円）
    price_adult = models.IntegerField(
        verbose_name="大人1名の料金",
    )

    # 子ども1名の料金（円）
    price_child = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="子ども1名の料金",
    )

    # 年齢条件（例：小学生以上）
    age_condition = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="年齢条件",
    )

    family_ok = models.BooleanField(
        default=False,
        verbose_name="親子で参加できる",
    )

    beginner_ok = models.BooleanField(
        default=False,
        verbose_name="初心者歓迎",
    )

    # 当日の流れ [{time, text}]
    flow = models.JSONField(
        null=True,
        blank=True,
        verbose_name="当日の流れ",
    )

    belongings = models.JSONField(
        null=True,
        blank=True,
        verbose_name="持ち物",
    )

    notes = models.JSONField(
        null=True,
        blank=True,
        verbose_name="注意事項",
    )

    cancel_policy = models.TextField(
        verbose_name="キャンセルポリシー",
    )

    # draft（下書き）/ public（公開）/ private（非公開）/ suspended（運営による掲載停止）
    publish_status = models.CharField(
        max_length=20,
        choices=PublishStatus.choices,
        default=PublishStatus.DRAFT,
        verbose_name="公開状態",
    )

    class Meta:
        db_table = "experiences"
        verbose_name = "体験プログラム"
        verbose_name_plural = "体験プログラム"

    def __str__(self):
        return self.title


class ExperienceImage(TimeStampedModel):
    """体験画像"""

    experience = models.ForeignKey(
        "marche.Experience",
        on_delete=models.CASCADE,
        related_name="experience_images",
        verbose_name="体験",
    )

    # 画像（S3のキー）
    image = models.ImageField(
        upload_to="experience_images/",
        max_length=500,
        verbose_name="画像",
    )

    sort_order = models.IntegerField(
        default=0,
        verbose_name="表示順",
    )

    class Meta:
        db_table = "experience_images"
        verbose_name = "体験画像"
        verbose_name_plural = "体験画像"
        ordering = ["sort_order", "id"]


class ExperienceSlot(TimeStampedModel):
    """開催日程

    MVPは1体験1日程でも動く。日程を分けておけば、予約枠管理（拡張）でスキーマを変えずに済む。"""

    class Status(models.TextChoices):
        OPEN = "open", "受付中"
        CLOSED = "closed", "締切"
        CANCELED = "canceled", "中止"

    experience = models.ForeignKey(
        "marche.Experience",
        on_delete=models.CASCADE,
        related_name="experience_slots",
        verbose_name="体験",
    )

    start_at = models.DateTimeField(
        verbose_name="開催日時",
    )

    # 所要時間（分）
    duration_min = models.IntegerField(
        verbose_name="所要時間",
    )

    capacity = models.IntegerField(
        verbose_name="定員",
    )

    reserved_count = models.IntegerField(
        default=0,
        verbose_name="予約済み人数",
    )

    # open / closed / canceled
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
        verbose_name="受付状態",
    )

    class Meta:
        db_table = "experience_slots"
        verbose_name = "開催日程"
        verbose_name_plural = "開催日程"


class Reservation(TimeStampedModel):
    """体験予約"""

    class Status(models.TextChoices):
        APPLIED = "applied", "申込済み"
        CONFIRMED = "confirmed", "確定"
        CANCELED = "canceled", "キャンセル"
        ATTENDED = "attended", "参加済み"

    reservation_no = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="予約番号",
    )

    slot = models.ForeignKey(
        "marche.ExperienceSlot",
        on_delete=models.PROTECT,
        related_name="reservations",
        verbose_name="開催日程",
    )

    # 予約した会員。ログイン必須
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reservations",
        verbose_name="予約した会員",
    )

    adult_count = models.IntegerField(
        verbose_name="大人の人数",
    )

    child_count = models.IntegerField(
        default=0,
        verbose_name="子どもの人数",
    )

    # 未就学児の人数（無料）
    infant_count = models.IntegerField(
        default=0,
        verbose_name="未就学児の人数",
    )

    representative_name = models.CharField(
        max_length=100,
        verbose_name="代表者氏名",
    )

    phone = models.CharField(
        max_length=20,
        verbose_name="当日の連絡先",
    )

    message = models.TextField(
        null=True,
        blank=True,
        verbose_name="生産者へのメッセージ",
    )

    # 合計金額（円）
    total_amount = models.IntegerField(
        verbose_name="合計金額",
    )

    # applied / confirmed / canceled / attended
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.APPLIED,
        verbose_name="予約状態",
    )

    policy_agreed_at = models.DateTimeField(
        verbose_name="キャンセルポリシーに同意した日時",
    )

    # オンライン決済（拡張）
    stripe_payment_intent_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Stripe 決済ID",
    )

    class Meta:
        db_table = "reservations"
        verbose_name = "体験予約"
        verbose_name_plural = "体験予約"

    def __str__(self):
        return self.reservation_no


class ExperienceReview(TimeStampedModel):
    """体験レビュー"""

    # 参加した予約。1予約につき1件
    reservation = models.OneToOneField(
        "marche.Reservation",
        on_delete=models.PROTECT,
        related_name="review",
        verbose_name="参加した予約",
    )

    # 体験（集計用）
    experience = models.ForeignKey(
        "marche.Experience",
        on_delete=models.PROTECT,
        related_name="experience_reviews",
        verbose_name="体験",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="experience_reviews",
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

    class Meta:
        db_table = "experience_reviews"
        verbose_name = "体験レビュー"
        verbose_name_plural = "体験レビュー"
