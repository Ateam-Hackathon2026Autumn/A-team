"""運営：問い合わせ・通報・お知らせ・操作ログ"""
from django.conf import settings
from django.db import models

from .base import TimeStampedModel


class Inquiry(TimeStampedModel):
    """問い合わせ

    特定の掲載内容への申し立ては通報（reports）で受ける。問い合わせは運営への質問・相談。"""

    class Category(models.TextChoices):
        ORDER = "order", "注文・配送"
        REFUND = "refund", "キャンセル・返金"
        EXPERIENCE = "experience", "体験の予約"
        JOB = "job", "求人・応募"
        ACCOUNT = "account", "アカウント・ログイン"
        PRODUCER_APPLICATION = "producer_application", "生産者登録・審査"
        LISTING = "listing", "出品・掲載"
        PAYOUT = "payout", "売上・入金"
        BUG = "bug", "不具合の報告"
        OTHER = "other", "その他"

    class Status(models.TextChoices):
        OPEN = "open", "未対応"
        IN_PROGRESS = "in_progress", "対応中"
        CLOSED = "closed", "完了"

    class Priority(models.TextChoices):
        HIGH = "high", "高"
        MEDIUM = "medium", "中"
        LOW = "low", "低"

    # 問い合わせた会員。未ログインなら空
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="inquiries_as_user",
        null=True,
        blank=True,
        verbose_name="問い合わせた会員",
    )

    # 関係する注文。注文履歴から問い合わせたときに自動で入れる
    order = models.ForeignKey(
        "marche.Order",
        on_delete=models.SET_NULL,
        related_name="inquiries",
        null=True,
        blank=True,
        verbose_name="関係する注文",
    )

    email = models.EmailField(
        max_length=254,
        verbose_name="返信先メールアドレス",
    )

    # order（注文・配送）/ refund（キャンセル・返金）/ experience（体験の予約）/ job（求人・応募）/ account（アカウント・ログイン）/ producer_application（生産者登録・審査）/ listing（出品・掲載）/ payout（売上・入金）/ bug（不具合の報告）/ other（その他）
    category = models.CharField(
        max_length=30,
        choices=Category.choices,
        verbose_name="種別",
    )

    subject = models.CharField(
        max_length=100,
        verbose_name="件名",
    )

    body = models.TextField(
        verbose_name="本文",
    )

    # open / in_progress / closed
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
        verbose_name="対応状態",
    )

    # high / medium / low
    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default="medium",
        verbose_name="優先度",
    )

    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="inquiries_as_assignee",
        null=True,
        blank=True,
        verbose_name="担当の運営スタッフ",
    )

    class Meta:
        db_table = "inquiries"
        verbose_name = "問い合わせ"
        verbose_name_plural = "問い合わせ"

    def __str__(self):
        return self.subject


class InquiryNote(TimeStampedModel):
    """問い合わせ対応履歴

    運営画面の「対応履歴」。いつ・誰が・何をしたかを1行ずつ積み上げる。"""

    inquiry = models.ForeignKey(
        "marche.Inquiry",
        on_delete=models.CASCADE,
        related_name="inquiry_notes",
        verbose_name="問い合わせ",
    )

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inquiry_notes",
        verbose_name="書いた運営スタッフ",
    )

    body = models.TextField(
        verbose_name="対応内容のメモ",
    )

    class Meta:
        db_table = "inquiry_notes"
        verbose_name = "問い合わせ対応履歴"
        verbose_name_plural = "問い合わせ対応履歴"


class Report(TimeStampedModel):
    """通報

    対象が6種類あるので target_type + target_id の汎用参照にした。外部キー制約は効かない（Django では GenericForeignKey）。"""

    class TargetType(models.TextChoices):
        PRODUCT = "product", "商品"
        EXPERIENCE = "experience", "体験"
        JOB = "job", "求人"
        STORY = "story", "ストーリー"
        PRODUCER = "producer", "生産者"
        USER = "user", "ユーザー"

    class Status(models.TextChoices):
        OPEN = "open", "未対応"
        RESOLVED = "resolved", "対応済み"
        DISMISSED = "dismissed", "対応不要"

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reports_as_reporter",
        verbose_name="通報した会員",
    )

    # product / experience / job / story / producer / user
    target_type = models.CharField(
        max_length=20,
        choices=TargetType.choices,
        verbose_name="対象の種類",
    )

    target_id = models.BigIntegerField(
        verbose_name="対象のID",
    )

    reason = models.CharField(
        max_length=30,
        verbose_name="通報理由",
    )

    detail = models.TextField(
        null=True,
        blank=True,
        verbose_name="詳細",
    )

    # open / resolved / dismissed
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
        verbose_name="対応状態",
    )

    handled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="reports_as_handled_by",
        null=True,
        blank=True,
        db_column="handled_by",
        verbose_name="対応した運営スタッフ",
    )

    class Meta:
        db_table = "reports"
        verbose_name = "通報"
        verbose_name_plural = "通報"


class Notice(TimeStampedModel):
    """お知らせ"""

    class Audience(models.TextChoices):
        ALL = "all", "全員"
        CONSUMER = "consumer", "消費者"
        PRODUCER = "producer", "生産者"

    title = models.CharField(
        max_length=100,
        verbose_name="タイトル",
    )

    body = models.TextField(
        verbose_name="本文",
    )

    # all / consumer / producer
    audience = models.CharField(
        max_length=20,
        choices=Audience.choices,
        verbose_name="公開対象",
    )

    published_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="公開日時",
    )

    class Meta:
        db_table = "notices"
        verbose_name = "お知らせ"
        verbose_name_plural = "お知らせ"

    def __str__(self):
        return self.title


class AuditLog(TimeStampedModel):
    """操作ログ"""

    admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="audit_logs",
        verbose_name="操作した運営スタッフ",
    )

    # approve / suspend / hide など
    action = models.CharField(
        max_length=30,
        verbose_name="操作内容",
    )

    target_type = models.CharField(
        max_length=30,
        verbose_name="対象の種類",
    )

    target_id = models.BigIntegerField(
        verbose_name="対象のID",
    )

    detail = models.JSONField(
        null=True,
        blank=True,
        verbose_name="変更前後の値",
    )

    class Meta:
        db_table = "audit_logs"
        verbose_name = "操作ログ"
        verbose_name_plural = "操作ログ"
