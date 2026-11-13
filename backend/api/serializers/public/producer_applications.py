"""生産者申請 のシリアライザー

使う view: api/views/public/producer_applications.py
形は Notion の「生産者登録API」「生産者申請状況取得API」「生産者申請修正・再申請API」に合わせる。
Notion から変えたもの（api-spec「7. 実装で決めたこと」）:
  - 文字数はER図に合わせる（businessName 100・city 50・productionItems 100）
  - 却下のあとも再申請できる（canResubmit は差し戻し・却下で true）
  - 状況取得の producer に profileImageUrl・coverImageUrl を足す
申請書類は今回は扱わない（拡張）。
"""
from django.utils import timezone
from rest_framework import serializers

from marche.models import Prefecture, Producer, ProducerApplication, PublishStatus

from ...common.images import ImageUrlField
from ...common.serializers import StrictSerializer

MAX_INT = 2 ** 31 - 1
MAX_ID = 2 ** 63 - 1
RESUBMITTABLE = [ProducerApplication.Status.RETURNED, ProducerApplication.Status.REJECTED]

# producers の列にそのまま入れる項目
PRODUCER_FIELDS = ["business_name", "representative_name", "genre", "prefecture_id", "city", "production_items",
                   "intro", "accepts_experience", "recruiting", "career_start_year", "founded_year", "profile_image",
                   "cover_image"]


# =========================================================
# リクエスト
# =========================================================

class ProducerApplicationFieldsSerializer(StrictSerializer):
    """申請する生産者情報（登録の本文・再申請の changes）。再申請では partial=True（1項目以上）

    文字列は前後の空白を除く。就業年・創業年は今年以下。都道府県はマスタにあるもの。
    画像キーが自分のアップロードしたものかは view で確かめる（services/storage.py）
    """

    business_name = serializers.CharField(max_length=100)
    representative_name = serializers.CharField(max_length=100)
    genre = serializers.ChoiceField(choices=Producer.Genre.choices)
    prefecture_id = serializers.IntegerField(min_value=1, max_value=MAX_INT)
    city = serializers.CharField(max_length=50)
    production_items = serializers.CharField(max_length=100)
    intro = serializers.CharField()
    accepts_experience = serializers.BooleanField()
    recruiting = serializers.BooleanField()
    career_start_year = serializers.IntegerField(min_value=1, max_value=9999, required=False, allow_null=True)
    founded_year = serializers.IntegerField(min_value=1, max_value=9999, required=False, allow_null=True)
    profile_image = serializers.CharField(max_length=500, required=False, allow_null=True)
    cover_image = serializers.CharField(max_length=500, required=False, allow_null=True)
    application_reason = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    def validate_prefecture_id(self, value):
        if not Prefecture.objects.filter(pk=value).exists():
            raise serializers.ValidationError("都道府県が見つかりません。")
        return value

    def validate_career_start_year(self, value):
        return self._not_future(value)

    def validate_founded_year(self, value):
        return self._not_future(value)

    def _not_future(self, year):
        if year is not None and year > timezone.localdate().year:
            raise serializers.ValidationError("今年以前の年を入力してください。")
        return year

    def validate_application_reason(self, value):
        return value or None

    def validate(self, attrs):
        if self.partial and not attrs:
            raise serializers.ValidationError({"non_field_errors": ["変更する項目を指定してください。"]})
        return attrs


class ResubmitSerializer(StrictSerializer):
    """PATCH /producer-applications/me の本文 {applicationId, changes}（changes の中身は view で検証する）"""

    application_id = serializers.IntegerField(min_value=1, max_value=MAX_ID)
    changes = serializers.DictField()


# =========================================================
# レスポンス
# =========================================================

class ApplicationAcceptedSerializer(serializers.Serializer):
    """登録・再申請のレスポンス"""

    message = serializers.CharField()
    producer_id = serializers.IntegerField(source="producer.id")
    application_id = serializers.IntegerField(source="application.id")
    approval_status = serializers.CharField(source="producer.approval_status")
    application_status = serializers.CharField(source="application.status")
    publish_status = serializers.CharField(source="producer.publish_status")
    is_producer = serializers.SerializerMethodField()
    submitted_at = serializers.DateTimeField(source="application.submitted_at")

    def get_is_producer(self, data):
        return False  # 承認されるまでは生産者の権限はない


class MyProducerSerializer(serializers.ModelSerializer):
    """修正画面の初期値になる、今の生産者情報＋最新の申請理由（view で application_reason を入れる）"""

    profile_image = serializers.SerializerMethodField()
    cover_image = serializers.SerializerMethodField()
    profile_image_url = ImageUrlField(source="profile_image")
    cover_image_url = ImageUrlField(source="cover_image")
    application_reason = serializers.SerializerMethodField()

    class Meta:
        model = Producer
        fields = PRODUCER_FIELDS + ["profile_image_url", "cover_image_url", "application_reason"]

    def get_profile_image(self, producer):
        return producer.profile_image.name or None

    def get_cover_image(self, producer):
        return producer.cover_image.name or None

    def get_application_reason(self, producer):
        return self.context["application"].application_reason or None


class MyApplicationSerializer(serializers.ModelSerializer):
    """GET /producer-applications/me（最新の申請1件）"""

    application_id = serializers.IntegerField(source="id")
    can_resubmit = serializers.SerializerMethodField()
    producer = serializers.SerializerMethodField()

    class Meta:
        model = ProducerApplication
        fields = ["application_id", "producer_id", "status", "review_comment", "submitted_at", "reviewed_at",
                  "can_resubmit", "producer"]

    def get_can_resubmit(self, application):
        return (application.status in RESUBMITTABLE
                and application.producer.publish_status != PublishStatus.SUSPENDED)

    def get_producer(self, application):
        return MyProducerSerializer(application.producer, context={"application": application}).data
