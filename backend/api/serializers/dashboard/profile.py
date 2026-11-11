"""生産者プロフィール のシリアライザー

使う view: api/views/dashboard/profile.py

  - 取得・更新のレスポンス: DashboardProfileSerializer
      ・画像のキーは申請APIと同じ profileImage・coverImage（＋表示用の profileImageUrl・coverImageUrl）
      ・農園画像は商品と同じ images [{id, key, url, sortOrder}]（producer_images を prefetch しておく）
      ・reason・goal・storyPublishStatus はストーリー（producer_stories）の値。表示用で、更新はストーリーAPIで行う
  - 更新の本文: ProfileUpdateSerializer（送った項目だけ。空のオブジェクト・未知の項目は400）
      ・事業者名・代表者名・ジャンルは変えられない（未知の項目として400）
      ・文字数は申請と同じ（city 50・productionItems 100）。年は今年以前
      ・imageKeys は10枚まで・重複なし。配列で置き換え、順番が表示順
      ・publishStatus は public・private だけ

入力エラーは 400（項目ごとのメッセージ）。カラム名は claude/er-diagram.md に合わせる
"""
from django.utils import timezone
from rest_framework import serializers

from marche.models import Prefecture, Producer, ProducerImage, PublishStatus

from ...common.images import ImageUrlField
from ...common.serializers import StrictSerializer

MAX_INT = 2 ** 31 - 1
MAX_IMAGES = 10


class ProducerImageSerializer(serializers.ModelSerializer):
    """{id, key, url, sortOrder}（key は更新の imageKeys にそのまま送れる）"""

    key = serializers.CharField(source="image.name")
    url = ImageUrlField(source="image")

    class Meta:
        model = ProducerImage
        fields = ["id", "key", "url", "sort_order"]


class DashboardProfileSerializer(serializers.ModelSerializer):
    profile_image = serializers.SerializerMethodField()
    cover_image = serializers.SerializerMethodField()
    profile_image_url = ImageUrlField(source="profile_image")
    cover_image_url = ImageUrlField(source="cover_image")
    images = ProducerImageSerializer(source="producer_images", many=True)
    reason = serializers.SerializerMethodField()
    goal = serializers.SerializerMethodField()
    story_publish_status = serializers.SerializerMethodField()

    class Meta:
        model = Producer
        fields = ["id", "business_name", "representative_name", "genre", "prefecture_id", "city", "production_items",
                  "intro", "career_start_year", "founded_year", "accepts_experience", "recruiting", "profile_image",
                  "cover_image", "profile_image_url", "cover_image_url", "images", "approval_status",
                  "publish_status", "reason", "goal", "story_publish_status", "updated_at"]

    def get_profile_image(self, producer):
        return producer.profile_image.name or None

    def get_cover_image(self, producer):
        return producer.cover_image.name or None

    @staticmethod
    def _story(producer):
        return getattr(producer, "story", None)

    def get_reason(self, producer):
        story = self._story(producer)
        return story.reason if story else None

    def get_goal(self, producer):
        story = self._story(producer)
        return story.goal if story else None

    def get_story_publish_status(self, producer):
        story = self._story(producer)
        return story.publish_status if story else None


class ProfileUpdateSerializer(StrictSerializer):
    prefecture_id = serializers.IntegerField(min_value=1, max_value=MAX_INT, required=False)
    city = serializers.CharField(max_length=50, required=False)
    production_items = serializers.CharField(max_length=100, required=False)
    intro = serializers.CharField(required=False)
    career_start_year = serializers.IntegerField(min_value=1, max_value=9999, required=False, allow_null=True)
    founded_year = serializers.IntegerField(min_value=1, max_value=9999, required=False, allow_null=True)
    accepts_experience = serializers.BooleanField(required=False)
    recruiting = serializers.BooleanField(required=False)
    profile_image = serializers.CharField(max_length=500, required=False, allow_null=True)
    cover_image = serializers.CharField(max_length=500, required=False, allow_null=True)
    image_keys = serializers.ListField(child=serializers.CharField(max_length=500), max_length=MAX_IMAGES,
                                       required=False)
    publish_status = serializers.ChoiceField(choices=[PublishStatus.PUBLIC, PublishStatus.PRIVATE], required=False)

    def validate_prefecture_id(self, value):
        if not Prefecture.objects.filter(pk=value).exists():
            raise serializers.ValidationError("都道府県が見つかりません。")
        return value

    def validate_career_start_year(self, value):
        return self._not_future(value)

    def validate_founded_year(self, value):
        return self._not_future(value)

    @staticmethod
    def _not_future(year):
        if year is not None and year > timezone.localdate().year:
            raise serializers.ValidationError("今年以前の年を入力してください。")
        return year

    def validate_image_keys(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError("同じ画像を複数指定することはできません。")
        return value

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError({"non_field_errors": ["変更する項目を指定してください。"]})
        return attrs
