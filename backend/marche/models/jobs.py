"""求人・勤務日・応募・給与支払い"""
from django.conf import settings
from django.db import models

from .base import PublishStatus, TimeStampedModel


class Job(TimeStampedModel):
    """求人

    エリアは prefecture_id → prefectures → areas でたどる（勤務地が生産者の所在地と違っても正しく検索できる）。ジャンルは producers.genre を使う。"""

    class TermType(models.TextChoices):
        ONE_DAY = "one_day", "単発"
        SHORT = "short", "短期"
        LONG = "long", "長期"

    class PayUnit(models.TextChoices):
        HOURLY = "hourly", "時給"
        DAILY = "daily", "日給"
        MONTHLY = "monthly", "月給"

    producer = models.ForeignKey(
        "marche.Producer",
        on_delete=models.PROTECT,
        related_name="jobs",
        verbose_name="募集する生産者",
    )

    # 勤務地の都道府県。エリア検索に使う。登録時は生産者の都道府県を初期値にする
    prefecture = models.ForeignKey(
        "marche.Prefecture",
        on_delete=models.PROTECT,
        related_name="jobs",
        verbose_name="勤務地の都道府県",
    )

    title = models.CharField(
        max_length=100,
        verbose_name="タイトル",
    )

    # one_day（単発）/ short（短期）/ long（長期）
    term_type = models.CharField(
        max_length=20,
        choices=TermType.choices,
        verbose_name="期間の種類",
    )

    # hourly（時給）/ daily（日給）/ monthly（月給）
    pay_unit = models.CharField(
        max_length=20,
        choices=PayUnit.choices,
        verbose_name="報酬の単位",
    )

    # 報酬額（円）
    pay_amount = models.IntegerField(
        verbose_name="報酬額",
    )

    period_start = models.DateField(
        null=True,
        blank=True,
        verbose_name="募集期間の開始",
    )

    period_end = models.DateField(
        null=True,
        blank=True,
        verbose_name="募集期間の終了",
    )

    # 勤務時間（例：8:00〜15:00）
    work_hours = models.CharField(
        max_length=50,
        verbose_name="勤務時間",
    )

    # 勤務地（市区町村以下の詳しい場所）
    work_place = models.CharField(
        max_length=200,
        verbose_name="勤務地",
    )

    slots = models.IntegerField(
        verbose_name="募集人数",
    )

    description = models.TextField(
        verbose_name="仕事内容",
    )

    requirements = models.JSONField(
        null=True,
        blank=True,
        verbose_name="応募条件",
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

    inexperienced_ok = models.BooleanField(
        default=False,
        verbose_name="未経験歓迎",
    )

    # メイン画像（S3のキー）
    cover_image = models.ImageField(
        upload_to="jobs/",
        max_length=500,
        null=True,
        blank=True,
        verbose_name="メイン画像",
    )

    # draft（下書き）/ public（公開）/ private（非公開）/ suspended（運営による掲載停止）
    publish_status = models.CharField(
        max_length=20,
        choices=PublishStatus.choices,
        default=PublishStatus.DRAFT,
        verbose_name="公開状態",
    )

    class Meta:
        db_table = "jobs"
        verbose_name = "求人"
        verbose_name_plural = "求人"

    def __str__(self):
        return self.title


class JobWorkDate(TimeStampedModel):
    """勤務日

    応募画面の「勤務希望日」の選択肢。長期求人では作らない。"""

    job = models.ForeignKey(
        "marche.Job",
        on_delete=models.CASCADE,
        related_name="job_work_dates",
        verbose_name="求人",
    )

    work_date = models.DateField(
        verbose_name="勤務日",
    )

    needed_count = models.IntegerField(
        verbose_name="その日の募集人数",
    )

    class Meta:
        db_table = "job_work_dates"
        verbose_name = "勤務日"
        verbose_name_plural = "勤務日"


class JobApplication(TimeStampedModel):
    """求人応募

    job_id + user_id でユニーク（同じ求人への二重応募を防ぐ）。最近動きがあった順は updated_at で並べる。すべての状態の履歴が必要になったら、履歴テーブルを別に作る（拡張）。"""

    class Status(models.TextChoices):
        APPLIED = "applied", "応募済み"
        SCREENING = "screening", "選考中"
        HIRED = "hired", "採用"
        REJECTED = "rejected", "却下"
        WITHDRAWN = "withdrawn", "辞退"
        COMPLETED = "completed", "勤務完了"

    job = models.ForeignKey(
        "marche.Job",
        on_delete=models.PROTECT,
        related_name="job_applications",
        verbose_name="求人",
    )

    # 応募した会員。ログイン必須
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="job_applications",
        verbose_name="応募した会員",
    )

    message = models.TextField(
        null=True,
        blank=True,
        verbose_name="ひとことメッセージ",
    )

    # あてはまるもの（任意のチェック項目）
    answers = models.JSONField(
        null=True,
        blank=True,
        verbose_name="あてはまるもの",
    )

    # applied / screening / hired / rejected / withdrawn / completed
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.APPLIED,
        verbose_name="応募状態",
    )

    # 採用・不採用を決めた日時。決める前は空
    decided_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="採用・不採用を決めた日時",
    )

    class Meta:
        db_table = "job_applications"
        verbose_name = "求人応募"
        verbose_name_plural = "求人応募"
        constraints = [
            models.UniqueConstraint(fields=['job', 'user'], name="uniq_job_applications_job_user"),
        ]


class ApplicationWorkDate(TimeStampedModel):
    """応募の希望日"""

    application = models.ForeignKey(
        "marche.JobApplication",
        on_delete=models.CASCADE,
        related_name="application_work_dates",
        verbose_name="応募",
    )

    work_date = models.ForeignKey(
        "marche.JobWorkDate",
        on_delete=models.CASCADE,
        related_name="application_work_dates",
        verbose_name="希望した勤務日",
    )

    class Meta:
        db_table = "application_work_dates"
        verbose_name = "応募の希望日"
        verbose_name_plural = "応募の希望日"
        constraints = [
            models.UniqueConstraint(fields=['application', 'work_date'], name="uniq_application_work_dates_application_work_date"),
        ]


class WagePayment(TimeStampedModel):
    """給与支払い"""

    class Status(models.TextChoices):
        PENDING = "pending", "支払い待ち"
        PAID = "paid", "支払い済み"
        FAILED = "failed", "失敗"

    # 応募（採用済み）
    job_application = models.ForeignKey(
        "marche.JobApplication",
        on_delete=models.PROTECT,
        related_name="wage_payments",
        verbose_name="応募",
    )

    work_date = models.DateField(
        verbose_name="勤務日",
    )

    # 支払額（円）
    amount = models.IntegerField(
        verbose_name="支払額",
    )

    # pending / paid / failed
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="支払い状態",
    )

    transfer_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="外部決済サービスの送金ID",
    )

    paid_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="支払日時",
    )

    class Meta:
        db_table = "wage_payments"
        verbose_name = "給与支払い"
        verbose_name_plural = "給与支払い"
