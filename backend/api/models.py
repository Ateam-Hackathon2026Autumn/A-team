ffrom django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """ユーザー"""

    class Role(models.TextChoices):
        CONSUMER = "consumer", "消費者"
        PRODUCER = "producer", "生産者"
        ADMIN = "admin", "管理者"

    class Status(models.TextChoices):
        ACTIVE = "active", "有効"
        SUSPENDED = "suspended", "停止"
        DELETED = "deleted", "削除"

    username = None

    email = models.EmailField(
        unique=True,
        verbose_name="メールアドレス",
    )

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CONSUMER,
        verbose_name="ロール",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        verbose_name="アカウント状態",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="作成日時",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="更新日時",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "USERS"
        verbose_name = "ユーザー"
        verbose_name_plural = "ユーザー"

    def __str__(self):
        return self.email