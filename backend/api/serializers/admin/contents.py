"""生産者・商品・体験・求人・ストーリーの管理（掲載停止・再開） のシリアライザー

使う view: api/views/admin/contents.py

  - 一覧のクエリ: ContentListQuerySerializer {keyword, publishStatus, producerId, page, pageSize}
      （生産者の一覧は producerId なしの ProducerListQuerySerializer）
  - 一覧の1件・詳細: 種類ごとの *ListItemSerializer・*DetailSerializer。共通の項目は id・publishStatus・
      producer {id, businessName, publishStatus}（生産者以外）・createdAt・updatedAt
      詳細の suspension は view で入れる（掲載停止中なら {reason, suspendedAt, suspendedBy}、ほかは null）
  - 掲載停止・再開の本文: StatusUpdateSerializer {action: suspend|resume, reason}（suspend は reason 必須・1,000文字まで）

入力エラーは 400（項目ごとのメッセージ）。カラム名は claude/er-diagram.md に合わせる
"""
from rest_framework import serializers

from marche.models import (Experience, ExperienceImage, Job, JobWorkDate, Producer, ProducerImage, ProducerStory,
                           Product, ProductImage, PublishStatus)

from ...common.images import ImageUrlField
from ...common.pagination import PageQuerySerializer
from ...common.serializers import StrictSerializer

MAX_ID = 2 ** 63 - 1


# =========================================================
# リクエスト
# =========================================================

class ProducerListQuerySerializer(PageQuerySerializer):
    keyword = serializers.CharField(required=False, max_length=100)
    publish_status = serializers.ChoiceField(choices=PublishStatus.choices, required=False)


class ContentListQuerySerializer(ProducerListQuerySerializer):
    producer_id = serializers.IntegerField(required=False, min_value=1, max_value=MAX_ID)


class StatusUpdateSerializer(StrictSerializer):
    action = serializers.ChoiceField(choices=["suspend", "resume"])
    reason = serializers.CharField(max_length=1000, required=False, allow_blank=True, allow_null=True)

    def validate(self, attrs):
        attrs["reason"] = attrs.get("reason") or None
        if attrs["action"] == "suspend" and attrs["reason"] is None:
            raise serializers.ValidationError({"reason": ["掲載停止の理由を入力してください。"]})
        return attrs


# =========================================================
# レスポンス
# =========================================================

class ProducerBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Producer
        fields = ["id", "business_name", "publish_status"]


class SuspensionMixin(serializers.Serializer):
    """view が obj.suspension に入れた値（掲載停止中でなければ null）"""

    suspension = serializers.SerializerMethodField()

    def get_suspension(self, obj):
        return getattr(obj, "suspension", None)


def image_serializer(image_model):
    class ImageSerializer(serializers.ModelSerializer):
        url = ImageUrlField(source="image")

        class Meta:
            model = image_model
            fields = ["id", "url", "sort_order"]
    return ImageSerializer


# --- 生産者 ---
PRODUCER_LIST_FIELDS = ["id", "business_name", "representative_name", "genre", "prefecture_name", "city", "email",
                        "user_active", "publish_status", "approved_at", "created_at", "updated_at"]


class ProducerListItemSerializer(serializers.ModelSerializer):
    prefecture_name = serializers.CharField(source="prefecture.name")
    email = serializers.CharField(source="user.email")
    user_active = serializers.SerializerMethodField()

    class Meta:
        model = Producer
        fields = PRODUCER_LIST_FIELDS

    def get_user_active(self, producer):
        """ログインアカウントが利用中か（利用停止・退会なら false）"""
        return producer.user.is_active and producer.user.deleted_at is None


class ProducerDetailSerializer(SuspensionMixin, ProducerListItemSerializer):
    phone = serializers.CharField(source="user.phone", allow_null=True)
    profile_image_url = ImageUrlField(source="profile_image")
    cover_image_url = ImageUrlField(source="cover_image")
    images = image_serializer(ProducerImage)(source="producer_images", many=True)
    story_id = serializers.SerializerMethodField()
    counts = serializers.SerializerMethodField()

    class Meta:
        model = Producer
        fields = PRODUCER_LIST_FIELDS + [
            "phone", "production_items", "intro", "career_start_year", "founded_year", "accepts_experience",
            "recruiting", "profile_image_url", "cover_image_url", "images", "story_id", "counts", "suspension"]

    def get_story_id(self, producer):
        story = getattr(producer, "story", None)
        return story.id if story else None

    def get_counts(self, producer):
        """この生産者の商品・体験・求人の数（すべての公開状態）"""
        return producer.content_counts


# --- 商品 ---
PRODUCT_LIST_FIELDS = ["id", "name", "price", "sale_price", "stock", "category_name", "publish_status", "producer",
                       "created_at", "updated_at"]


class ProductListItemSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name")
    producer = ProducerBriefSerializer()

    class Meta:
        model = Product
        fields = PRODUCT_LIST_FIELDS


class ProductDetailSerializer(SuspensionMixin, ProductListItemSerializer):
    images = image_serializer(ProductImage)(source="product_images", many=True)

    class Meta:
        model = Product
        fields = PRODUCT_LIST_FIELDS + [
            "volume", "description", "method", "tax_rate", "discount_rate", "is_subscription", "is_preorder",
            "accepts_delivery_date", "rating_avg", "review_count", "images", "suspension"]


# --- 体験 ---
EXPERIENCE_LIST_FIELDS = ["id", "title", "price_adult", "prefecture_name", "publish_status", "producer",
                          "created_at", "updated_at"]


class ExperienceListItemSerializer(serializers.ModelSerializer):
    prefecture_name = serializers.CharField(source="prefecture.name")
    producer = ProducerBriefSerializer()

    class Meta:
        model = Experience
        fields = EXPERIENCE_LIST_FIELDS


class ExperienceDetailSerializer(SuspensionMixin, ExperienceListItemSerializer):
    images = image_serializer(ExperienceImage)(source="experience_images", many=True)
    upcoming_reservation_count = serializers.IntegerField()

    class Meta:
        model = Experience
        fields = EXPERIENCE_LIST_FIELDS + [
            "description", "place", "price_child", "age_condition", "family_ok", "beginner_ok", "flow", "belongings",
            "notes", "booking_deadline_hours", "cancel_policy", "images", "upcoming_reservation_count", "suspension"]


# --- 求人 ---
JOB_LIST_FIELDS = ["id", "title", "term_type", "pay_unit", "pay_amount", "prefecture_name", "publish_status",
                   "producer", "created_at", "updated_at"]


class WorkDateSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobWorkDate
        fields = ["id", "work_date", "needed_count"]


class JobListItemSerializer(serializers.ModelSerializer):
    prefecture_name = serializers.CharField(source="prefecture.name")
    producer = ProducerBriefSerializer()

    class Meta:
        model = Job
        fields = JOB_LIST_FIELDS


class JobDetailSerializer(SuspensionMixin, JobListItemSerializer):
    cover_image_url = ImageUrlField(source="cover_image")
    work_dates = WorkDateSerializer(source="job_work_dates", many=True)
    open_application_count = serializers.IntegerField()

    class Meta:
        model = Job
        fields = JOB_LIST_FIELDS + [
            "period_start", "period_end", "work_hours", "work_place", "slots", "description", "requirements",
            "belongings", "notes", "inexperienced_ok", "cover_image_url", "work_dates", "open_application_count",
            "suspension"]


# --- ストーリー（producer_stories） ---
STORY_LIST_FIELDS = ["id", "publish_status", "producer", "created_at", "updated_at"]


class StoryListItemSerializer(serializers.ModelSerializer):
    producer = ProducerBriefSerializer()

    class Meta:
        model = ProducerStory
        fields = STORY_LIST_FIELDS


class StoryDetailSerializer(SuspensionMixin, StoryListItemSerializer):
    class Meta:
        model = ProducerStory
        fields = STORY_LIST_FIELDS + ["craft", "method", "process", "environment", "reason", "goal", "suspension"]
