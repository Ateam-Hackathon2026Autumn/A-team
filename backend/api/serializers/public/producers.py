"""生産者・学ぶ（公開側） のシリアライザー

使う view: api/views/public/producers.py
形は Notion の「生産者一覧取得API」「生産者プロフィール取得API」「生産者ストーリー取得API」に合わせる。
Notion から変えたもの（api-spec「7. 実装で決めたこと」）:
  - 一覧に hasStory の絞り込みと hasPublicStory を追加。一覧・詳細に isFavorited を追加
  - badges から featured を外す（注目は絞り込み・並び順だけ）
  - 詳細に応援ブロック（craft・reason・goal）を追加
  - ストーリーは ER図の producer_stories の形（category・title はなく craft がある）。producer（一覧の1件の形）を追加

返さないもの: user_id・連絡先・生年月日・申請書類・審査情報・Stripe 情報・注目スコア・S3 のキー
"""
from rest_framework import serializers

from marche.models import Producer, ProducerImage, ProducerStory, PublishStatus

from ...common.images import ImageUrlField
from ...common.pagination import PageQuerySerializer
from ...common.serializers import QueryBooleanField
from ...services.badges import badges_for

# INT・BIGINT の上限。これより大きい ID は DB に渡さない
MAX_INT_ID = 2 ** 31 - 1
MAX_ID = 2 ** 63 - 1

# 応援ブロックとストーリーの項目
SUPPORT_FIELDS = ["craft", "reason", "goal"]
STORY_FIELDS = ["craft", "method", "process", "environment", "reason", "goal"]


def public_story_text(producer, field):
    """公開中のストーリーの項目。ストーリーがない・公開中でない・空なら None"""
    story = getattr(producer, "story", None)
    if story is None or story.publish_status != PublishStatus.PUBLIC:
        return None
    return getattr(story, field) or None


# =========================================================
# リクエスト（クエリパラメーター）
# =========================================================

class ProducerListQuerySerializer(PageQuerySerializer):
    """GET /producers の ?featured=&newFarmer=&hasStory=&genre=&prefectureId=&sort=&page=&pageSize=

    真偽値は true / false だけ（false・省略は絞り込みなし）。条件はすべて AND
    """

    featured = QueryBooleanField(required=False)
    new_farmer = QueryBooleanField(required=False)
    has_story = QueryBooleanField(required=False)
    genre = serializers.ChoiceField(choices=Producer.Genre.choices, required=False)
    prefecture_id = serializers.IntegerField(required=False, min_value=1, max_value=MAX_INT_ID)
    sort = serializers.ChoiceField(choices=["newest", "featured"], required=False, default="newest")


# =========================================================
# レスポンス
# =========================================================

class PublicProducerSerializer(serializers.ModelSerializer):
    """生産者カード1枚分（一覧の1件・ストーリーの producer）

    view で次の注釈を付けた QuerySet を渡す（views/public/producers.py の annotate_producers）:
      - has_public_story: 公開中のストーリーがあるか / is_favorited: ログイン中の会員のお気に入りにあるか
    badges は context の now（リクエストごとに1回作る）で判定する
    """

    prefecture_name = serializers.CharField(source="prefecture.name")
    profile_image_url = ImageUrlField(source="profile_image")
    cover_image_url = ImageUrlField(source="cover_image")
    badges = serializers.SerializerMethodField()
    has_public_story = serializers.BooleanField()
    is_favorited = serializers.BooleanField()

    class Meta:
        model = Producer
        fields = ["id", "business_name", "genre", "prefecture_id", "prefecture_name", "city", "production_items",
                  "profile_image_url", "cover_image_url", "career_start_year", "founded_year", "accepts_experience",
                  "recruiting", "badges", "has_public_story", "is_favorited"]

    def get_badges(self, producer):
        return badges_for(producer, self.context.get("now"))


class ProducerImageSerializer(serializers.ModelSerializer):
    """{id, url, sortOrder}"""

    url = ImageUrlField(source="image")

    class Meta:
        model = ProducerImage
        fields = ["id", "url", "sort_order"]


class ProducerProfileSerializer(PublicProducerSerializer):
    """生産者プロフィール = カードの項目＋代表者名・紹介・農園画像・応援ブロック（craft・reason・goal）

    商品・体験・求人はここに入れない（各一覧APIを producerId 付きで呼ぶ）
    """

    images = ProducerImageSerializer(source="producer_images", many=True)
    craft = serializers.SerializerMethodField()
    reason = serializers.SerializerMethodField()
    goal = serializers.SerializerMethodField()

    class Meta(PublicProducerSerializer.Meta):
        fields = PublicProducerSerializer.Meta.fields + ["representative_name", "intro", "images"] + SUPPORT_FIELDS

    def get_craft(self, producer):
        return public_story_text(producer, "craft")

    def get_reason(self, producer):
        return public_story_text(producer, "reason")

    def get_goal(self, producer):
        return public_story_text(producer, "goal")


class ProducerStorySerializer(serializers.ModelSerializer):
    """学ぶページのストーリー（producer_stories。1生産者につき1件）。空の項目は null

    producer には注釈付きの生産者を view で入れておく（story.producer）
    """

    producer = PublicProducerSerializer()

    class Meta:
        model = ProducerStory
        fields = ["id", "producer_id"] + STORY_FIELDS + ["updated_at", "producer"]

    def to_representation(self, story):
        data = super().to_representation(story)
        for field in STORY_FIELDS:
            data[field] = data[field] or None
        return data
