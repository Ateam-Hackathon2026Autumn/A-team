from django.contrib.auth.models import AbstractUser
from django.db import models


# ==========================================
# 1. ユーザー
# ==========================================
class User(AbstractUser):

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

    # 基本情報
    name = models.CharField(
        max_length=50,
        verbose_name="氏名",
    )

    phone = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="電話番号",
    )

    birth_date = models.DateField(
        verbose_name="生年月日",
    )

    profile_image = models.URLField(
        max_length=1000,
        blank=True,
        null=True,
        verbose_name="プロフィール画像",
    )

    deleted_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="退会日時",
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

# ==========================================
# 2. 消費者プロフィール
# ==========================================
class ConsumerProfile(models.Model):
    user = models.OneToOneField(
        "api.User",
        on_delete=models.CASCADE,
        related_name="consumer_profile",
    )
    name = models.CharField(max_length=100)
    profile_image = models.URLField(blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = "CONSUMER_PROFILES"

    def __str__(self):
        return self.name


# ==========================================
# 3. 生産者
# ==========================================
class Producer(models.Model):
    class ApprovalStatus(models.TextChoices):
        PENDING = "pending", "審査中"
        APPROVED = "approved", "承認"
        REJECTED = "rejected", "却下"
        RETURNED = "returned", "差し戻し"

    user = models.OneToOneField(
        "api.User",
        on_delete=models.CASCADE,
        related_name="producer",
    )
    area = models.ForeignKey(
        "api.Area",
        on_delete=models.PROTECT,
        related_name="producers",
    )
    business_name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    address = models.CharField(max_length=255)
    production_items = models.TextField(blank=True, null=True)
    production_policy = models.TextField(blank=True,null=True,verbose_name="生産方針",)
    farming_reason = models.TextField(blank=True, null=True)
    future_goal = models.TextField(blank=True, null=True)
    farming_start_year = models.PositiveSmallIntegerField(blank=True, null=True)
    experience_available = models.BooleanField(default=False)
    job_recruiting = models.BooleanField(default=False)
    approval_status = models.CharField(
        max_length=20,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING,
    )
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "PRODUCERS"

    def __str__(self):
        return self.business_name


# ==========================================
# 4. 生産者登録申請
# ==========================================
class ProducerApplication(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "審査中"
        APPROVED = "approved", "承認"
        REJECTED = "rejected", "却下"
        RETURNED = "returned", "差し戻し"

    user = models.ForeignKey(
        "api.User",
        on_delete=models.CASCADE,
        related_name="producer_applications",
    )
    business_name = models.CharField(max_length=200)
    application_reason = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    admin_comment = models.TextField(blank=True, null=True)
    applied_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(blank=True, null=True)
    reviewed_by = models.ForeignKey(
        "api.User",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="reviewed_producer_applications",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "PRODUCER_APPLICATIONS"


# ==========================================
# 5. 生産者画像
# ==========================================
class ProducerImage(models.Model):
    class ImageType(models.TextChoices):
        PROFILE = "profile", "プロフィール"
        FARM = "farm", "農場"

    producer = models.ForeignKey(
        "api.Producer",
        on_delete=models.CASCADE,
        related_name="images",
    )
    image_url = models.URLField(max_length=1000)
    image_type = models.CharField(
        max_length=20,
        choices=ImageType.choices,
        default=ImageType.FARM,
    )
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "PRODUCER_IMAGES"
        ordering = ["sort_order", "id"]


# ==========================================
# 6. カテゴリ
# ==========================================
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = "CATEGORIES"

    def __str__(self):
        return self.name


# ==========================================
# 7. 商品
# ==========================================
class Product(models.Model):
    producer = models.ForeignKey(
        "api.Producer",
        on_delete=models.CASCADE,
        related_name="products",
    )
    category = models.ForeignKey(
        "api.Category",
        on_delete=models.PROTECT,
        related_name="products",
    )
    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True, null=True)
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "PRODUCTS"

    def __str__(self):
        return self.name


# ==========================================
# 8. 商品画像
# ==========================================
class ProductImage(models.Model):
    product = models.ForeignKey(
        "api.Product",
        on_delete=models.CASCADE,
        related_name="images",
    )
    image_url = models.URLField(max_length=1000)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "PRODUCT_IMAGES"
        ordering = ["sort_order", "id"]


# ==========================================
# 9. 体験
# ==========================================
class Experience(models.Model):
    producer = models.ForeignKey(
        "api.Producer",
        on_delete=models.CASCADE,
        related_name="experiences",
    )
    area = models.ForeignKey(
        "api.Area",
        on_delete=models.PROTECT,
        related_name="experiences",
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    location = models.CharField(max_length=255)
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    capacity = models.PositiveIntegerField()
    family_allowed = models.BooleanField(default=False)
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "EXPERIENCES"

    def __str__(self):
        return self.title


# ==========================================
# 10. 体験画像
# ==========================================
class ExperienceImage(models.Model):
    experience = models.ForeignKey(
        "api.Experience",
        on_delete=models.CASCADE,
        related_name="images",
    )
    image_url = models.URLField(max_length=1000)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "EXPERIENCE_IMAGES"
        ordering = ["sort_order", "id"]


# ==========================================
# 11. 体験申込
# ==========================================
class ExperienceApplication(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "申込中"
        APPROVED = "approved", "承認"
        CANCELLED = "cancelled", "キャンセル"
        COMPLETED = "completed", "完了"

    experience = models.ForeignKey(
        "api.Experience",
        on_delete=models.CASCADE,
        related_name="applications",
    )
    user = models.ForeignKey(
        "api.User",
        on_delete=models.CASCADE,
        related_name="experience_applications",
    )
    participant_count = models.PositiveIntegerField(default=1)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    applied_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "EXPERIENCE_APPLICATIONS"


# ==========================================
# 12. 求人
# ==========================================
class Job(models.Model):
    producer = models.ForeignKey(
        "api.Producer",
        on_delete=models.CASCADE,
        related_name="jobs",
    )
    area = models.ForeignKey(
        "api.Area",
        on_delete=models.PROTECT,
        related_name="jobs",
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    requirements = models.TextField(blank=True, null=True)
    workplace = models.CharField(max_length=255)
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField(blank=True, null=True)
    salary = models.DecimalField(max_digits=10, decimal_places=2)
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "JOBS"

    def __str__(self):
        return self.title


# ==========================================
# 13. 求人応募
# ==========================================
class JobApplication(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "応募中"
        ACCEPTED = "accepted", "採用"
        REJECTED = "rejected", "不採用"
        WITHDRAWN = "withdrawn", "辞退"

    job = models.ForeignKey(
        "api.Job",
        on_delete=models.CASCADE,
        related_name="applications",
    )
    user = models.ForeignKey(
        "api.User",
        on_delete=models.CASCADE,
        related_name="job_applications",
    )
    motivation = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    applied_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "JOB_APPLICATIONS"


# ==========================================
# 14. 生産者ストーリー
# ==========================================
class Story(models.Model):
    producer = models.ForeignKey(
        "api.Producer",
        on_delete=models.CASCADE,
        related_name="stories",
    )
    title = models.CharField(max_length=200)
    cultivation_method = models.TextField(blank=True, null=True)
    production_process = models.TextField(blank=True, null=True)
    policy = models.TextField(blank=True, null=True)
    content = models.TextField(blank=True, null=True)
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "STORIES"

    def __str__(self):
        return self.title


# ==========================================
# 15. 商品お気に入り
# ==========================================
class ProductFavorite(models.Model):
    user = models.ForeignKey(
        "api.User",
        on_delete=models.CASCADE,
        related_name="product_favorites",
    )
    product = models.ForeignKey(
        "api.Product",
        on_delete=models.CASCADE,
        related_name="favorites",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "PRODUCT_FAVORITES"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "product"],
                name="unique_product_favorite",
            ),
        ]


# ==========================================
# 16. 生産者お気に入り
# ==========================================
class ProducerFavorite(models.Model):
    user = models.ForeignKey(
        "api.User",
        on_delete=models.CASCADE,
        related_name="producer_favorites",
    )
    producer = models.ForeignKey(
        "api.Producer",
        on_delete=models.CASCADE,
        related_name="favorites",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "PRODUCER_FAVORITES"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "producer"],
                name="unique_producer_favorite",
            ),
        ]


# ==========================================
# 17. エリア
# ==========================================
class Area(models.Model):
    prefecture = models.ForeignKey(
        "api.Prefecture",
        on_delete=models.PROTECT,
        related_name="areas",
        verbose_name="都道府県",
    )

    city = models.CharField(
        max_length=100,
        verbose_name="市区町村",
    )

    name = models.CharField(
        max_length=100,
        verbose_name="エリア名",
    )

    class Meta:
        db_table = "AREAS"
        verbose_name = "エリア"
        verbose_name_plural = "エリア"

    def __str__(self):
        return f"{self.prefecture.name} {self.city} {self.name}"


# ==========================================
# 18. 都道府県
# ==========================================
class Prefecture(models.Model):
    name = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="都道府県名",
    )

    region = models.CharField(
        max_length=50,
        verbose_name="地方名",
    )

    class Meta:
        db_table = "PREFECTURES"
        verbose_name = "都道府県"
        verbose_name_plural = "都道府県"

    def __str__(self):
        return self.name


# ==========================================
# 19. 住所
# ==========================================
class Address(models.Model):
    user = models.ForeignKey(
        "api.User",
        on_delete=models.CASCADE,
        related_name="addresses",
        verbose_name="ユーザー",
    )

    recipient_name = models.CharField(
        max_length=100,
        verbose_name="宛名",
    )

    postal_code = models.CharField(
        max_length=10,
        verbose_name="郵便番号",
    )

    prefecture = models.ForeignKey(
        "api.Prefecture",
        on_delete=models.PROTECT,
        related_name="addresses",
        verbose_name="都道府県",
    )

    city = models.CharField(
        max_length=100,
        verbose_name="市区町村",
    )

    address_line1 = models.CharField(
        max_length=255,
        verbose_name="住所1",
    )

    address_line2 = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="住所2",
    )

    phone = models.CharField(
        max_length=50,
        verbose_name="電話番号",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="作成日時",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="更新日時",
    )

    class Meta:
        db_table = "ADDRESSES"
        verbose_name = "住所"
        verbose_name_plural = "住所"

    def __str__(self):
        return f"{self.recipient_name} - {self.postal_code}"