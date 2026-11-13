"""ストーリー記事とタグ（拡張）"""
from django.db import models

from .base import PublishStatus, TimeStampedModel


class StoryCategory(models.Model):
    """ストーリーのタグ

    マスタ。学ぶページのタグ。追加・名前の変更・並べ替えは行の編集だけで済み、コードもカラムも変わらない。"""

    id = models.AutoField(
        primary_key=True,
    )

    # 栽培方法 / 生産工程 / 環境への取り組み / 就農した理由 / 今後の目標
    name = models.CharField(
        max_length=30,
        unique=True,
        verbose_name="タグ名",
    )

    sort_order = models.IntegerField(
        default=0,
        verbose_name="表示順",
    )

    class Meta:
        db_table = "story_categories"
        verbose_name = "ストーリーのタグ"
        verbose_name_plural = "ストーリーのタグ"
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.name


class Story(TimeStampedModel):
    """ストーリー記事

    自由に何本でも書ける記事（季節の近況など）。拡張機能。学ぶページの決まった項目は producer_stories に1つずつ持つ。"""

    producer = models.ForeignKey(
        "marche.Producer",
        on_delete=models.PROTECT,
        related_name="stories",
        verbose_name="書いた生産者",
    )

    story_category = models.ForeignKey(
        "marche.StoryCategory",
        on_delete=models.PROTECT,
        related_name="stories",
        verbose_name="タグ",
    )

    title = models.CharField(
        max_length=100,
        verbose_name="タイトル",
    )

    lead = models.CharField(
        max_length=200,
        verbose_name="リード文",
    )

    body = models.TextField(
        verbose_name="本文",
    )

    # カバー画像（S3のキー）
    cover_image = models.ImageField(
        upload_to="stories/",
        max_length=500,
        null=True,
        blank=True,
        verbose_name="カバー画像",
    )

    # draft（下書き）/ public（公開）/ private（非公開）/ suspended（運営による掲載停止）
    publish_status = models.CharField(
        max_length=20,
        choices=PublishStatus.choices,
        default=PublishStatus.DRAFT,
        verbose_name="公開状態",
    )

    published_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="公開日時",
    )

    class Meta:
        db_table = "stories"
        verbose_name = "ストーリー記事"
        verbose_name_plural = "ストーリー記事"

    def __str__(self):
        return self.title
