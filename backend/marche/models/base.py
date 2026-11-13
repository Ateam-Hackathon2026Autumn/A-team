"""共通の抽象モデルと選択肢"""
from django.db import models

class TimeStampedModel(models.Model):
    """マスタ以外の全テーブルに作成・更新日時を付ける"""

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="作成日時",
    )

    # 更新日時（作成時は created_at と同じ値）
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="更新日時",
    )

    class Meta:
        abstract = True

class PublishStatus(models.TextChoices):
    """生産者・商品・体験・求人・ストーリーで共通の公開状態"""

    DRAFT = "draft", "下書き"
    PUBLIC = "public", "公開"
    PRIVATE = "private", "非公開"
    SUSPENDED = "suspended", "運営による掲載停止"
