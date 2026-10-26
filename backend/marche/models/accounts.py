"""アカウント・住所マスタ"""
from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

from .base import TimeStampedModel


class UserManager(BaseUserManager):
    """email でログインするためのマネージャー（username を使わない）"""

    use_in_migrations = True

    def _create_user(self, email, password, **extra):
        if not email:
            raise ValueError("メールアドレスは必須です")
        user = self.model(email=self.normalize_email(email), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        if not extra["is_staff"] or not extra["is_superuser"]:
            raise ValueError("スーパーユーザーは is_staff と is_superuser が True である必要があります")
        return self._create_user(email, password, **extra)

class User(AbstractUser):
    """ユーザー

    AbstractUser を継承し、username を外して email でログインする。
    消費者・生産者・運営の全員がここに1行持つ。生産者かどうかは producer（producers の行）の有無、
    運営かどうかは is_staff で判定する。運営スタッフの権限は Django 標準の Groups（users_groups）で管理する。
    is_active / is_staff / is_superuser / last_login / date_joined / password は AbstractUser 由来。
    """

    username = None

    # メールアドレス。ログインIDとして使う
    email = models.EmailField(
        max_length=254,
        unique=True,
        verbose_name="メールアドレス",
    )

    last_name = models.CharField(
        max_length=50,
        verbose_name="姓",
    )

    first_name = models.CharField(
        max_length=50,
        verbose_name="名",
    )

    # 電話番号。体験予約・求人応募の連絡先
    phone = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name="電話番号",
    )

    # 生年月日。求人の年齢条件の確認用
    birth_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="生年月日",
    )

    # 会員のプロフィール画像（S3のキー）
    profile_image = models.ImageField(
        upload_to="users/",
        max_length=500,
        null=True,
        blank=True,
        verbose_name="会員のプロフィール画像",
    )

    # 退会日時。利用停止と退会を見分ける
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="退会日時",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="更新日時",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["last_name", "first_name"]

    objects = UserManager()

    class Meta:
        db_table = "users"  # 中間テーブルは自動で users_groups / users_user_permissions になる
        verbose_name = "ユーザー"
        verbose_name_plural = "ユーザー"

    def __str__(self):
        return self.email

    @property
    def is_producer(self):
        return hasattr(self, "producer")


class Area(models.Model):
    """エリア

    マスタ（7行）。体験・求人の「エリアから探す」のタグ一覧。"""

    id = models.AutoField(
        primary_key=True,
    )

    # 北海道 / 東北 / 関東 / 中部 / 近畿 / 中国・四国 / 九州・沖縄
    name = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="エリア名",
    )

    # 表示順。id は変えずに並びだけ変えられる
    sort_order = models.IntegerField(
        default=0,
        verbose_name="表示順",
    )

    class Meta:
        db_table = "areas"
        verbose_name = "エリア"
        verbose_name_plural = "エリア"
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.name


class Prefecture(models.Model):
    """都道府県

    マスタ（47行）。エリアはここから引くので、producers などに area_id は持たせない。"""

    # JISコード（01〜47）
    id = models.PositiveSmallIntegerField(
        primary_key=True,
        verbose_name="JISコード",
    )

    area = models.ForeignKey(
        "marche.Area",
        on_delete=models.PROTECT,
        related_name="prefectures",
        verbose_name="所属エリア",
    )

    name = models.CharField(
        max_length=10,
        unique=True,
        verbose_name="都道府県名",
    )

    class Meta:
        db_table = "prefectures"
        verbose_name = "都道府県"
        verbose_name_plural = "都道府県"

    def __str__(self):
        return self.name


class Address(TimeStampedModel):
    """お届け先

    会員の住所録。1人で複数件（自宅・実家・贈答先）持てる。注文時は値を orders にコピーするので、編集・削除しても過去の注文は変わらない。"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="addresses",
        verbose_name="登録した会員",
    )

    recipient_name = models.CharField(
        max_length=100,
        verbose_name="受取人名",
    )

    postal_code = models.CharField(
        max_length=8,
        verbose_name="郵便番号",
    )

    # 都道府県。地域別送料（拡張）にも使う
    prefecture = models.ForeignKey(
        "marche.Prefecture",
        on_delete=models.PROTECT,
        related_name="addresses",
        verbose_name="都道府県",
    )

    # 市区町村（郵便番号から自動入力）
    city = models.CharField(
        max_length=50,
        verbose_name="市区町村",
    )

    address_line1 = models.CharField(
        max_length=100,
        verbose_name="町域・番地",
    )

    address_line2 = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="建物名・部屋番号",
    )

    phone = models.CharField(
        max_length=20,
        verbose_name="受取人の電話番号",
    )

    is_default = models.BooleanField(
        default=False,
        verbose_name="いつも使うお届け先",
    )

    class Meta:
        db_table = "addresses"
        verbose_name = "お届け先"
        verbose_name_plural = "お届け先"
