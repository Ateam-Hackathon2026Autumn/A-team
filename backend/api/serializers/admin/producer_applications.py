"""生産者審査（管理者） のシリアライザー

使う view: api/views/admin/producer_applications.py
Notion には名前だけで定義がないので、形は api-spec.md と「7. 実装で決めたこと」で決めた。申請書類は扱わない。
"""
from rest_framework import serializers

from marche.models import Producer, ProducerApplication

from ...common.images import ImageUrlField
from ...common.pagination import PageQuerySerializer
from ...common.serializers import StrictSerializer

STATUS_CHOICES = [status for status, _ in ProducerApplication.Status.choices] + ["all"]


# =========================================================
# リクエスト
# =========================================================

class ApplicationListQuerySerializer(PageQuerySerializer):
    """GET /admin/producer-applications の ?status=&page=&pageSize=

    status: pending（初期値・申請日の古い順）/ approved / rejected / returned / all（どれも申請日の新しい順）
    """

    status = serializers.ChoiceField(choices=STATUS_CHOICES, required=False, default="pending")


class ReviewCommentSerializer(StrictSerializer):
    """却下・差し戻しの本文 {reviewComment}（申請者に見せる理由）"""

    review_comment = serializers.CharField(max_length=1000)


# =========================================================
# レスポンス
# =========================================================

def full_name(user):
    return f"{user.last_name} {user.first_name}"


class ApplicantSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(source="id")
    name = serializers.SerializerMethodField()
    email = serializers.EmailField()

    def get_name(self, user):
        return full_name(user)


class ApplicantDetailSerializer(ApplicantSerializer):
    phone = serializers.CharField(allow_null=True)
    email_verified = serializers.SerializerMethodField()

    def get_email_verified(self, user):
        return user.email_verified_at is not None


class ApplicationProducerSummarySerializer(serializers.ModelSerializer):
    prefecture_name = serializers.CharField(source="prefecture.name")

    class Meta:
        model = Producer
        fields = ["id", "business_name", "representative_name", "genre", "prefecture_name", "city"]


class ApplicationListItemSerializer(serializers.ModelSerializer):
    """申請一覧の1件。producer・都道府県・申請者は select_related しておく"""

    application_id = serializers.IntegerField(source="id")
    producer = ApplicationProducerSummarySerializer()
    applicant = ApplicantSerializer(source="producer.user")

    class Meta:
        model = ProducerApplication
        fields = ["application_id", "status", "submitted_at", "reviewed_at", "producer", "applicant"]


class ApplicationProducerDetailSerializer(serializers.ModelSerializer):
    prefecture_name = serializers.CharField(source="prefecture.name")
    profile_image_url = ImageUrlField(source="profile_image")
    cover_image_url = ImageUrlField(source="cover_image")

    class Meta:
        model = Producer
        fields = ["id", "business_name", "representative_name", "genre", "prefecture_id", "prefecture_name", "city",
                  "production_items", "intro", "career_start_year", "founded_year", "accepts_experience",
                  "recruiting", "profile_image_url", "cover_image_url", "approval_status", "approved_at",
                  "publish_status"]


class ApplicationHistorySerializer(serializers.ModelSerializer):
    application_id = serializers.IntegerField(source="id")
    application_reason = serializers.SerializerMethodField()

    class Meta:
        model = ProducerApplication
        fields = ["application_id", "status", "application_reason", "review_comment", "submitted_at", "reviewed_at"]

    def get_application_reason(self, application):
        return application.application_reason or None


class ApplicationDetailSerializer(ApplicationHistorySerializer):
    """申請詳細。view で history（同じ生産者の他の申請）を入れておく"""

    reviewer_name = serializers.SerializerMethodField()
    producer = ApplicationProducerDetailSerializer()
    applicant = ApplicantDetailSerializer(source="producer.user")
    history = ApplicationHistorySerializer(many=True)

    class Meta(ApplicationHistorySerializer.Meta):
        fields = ApplicationHistorySerializer.Meta.fields + ["reviewer_name", "producer", "applicant", "history"]

    def get_reviewer_name(self, application):
        return full_name(application.reviewer) if application.reviewer else None
