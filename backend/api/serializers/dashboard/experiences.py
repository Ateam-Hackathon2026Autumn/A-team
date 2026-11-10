"""体験管理・予約枠・申込者 のシリアライザー

使う view: api/views/dashboard/experiences.py
レスポンスの形は Notion の API 定義、カラム名は claude/er-diagram.md に合わせる。
キーは Python ではスネークケースで書き、レスポンス時にキャメルケースへ自動変換される。

- リクエストの検証: StrictSerializer / QuerySerializer を継承（定義にない項目・重複したクエリは 400）
- 入力エラーは 400（項目ごとのメッセージ）。状態の衝突（409）は view で判定する
"""
from django.utils import timezone
from rest_framework import serializers

from marche.models import Experience, ExperienceSlot, Prefecture, PublishStatus, Reservation

from ...common.images import ImageUrlField
from ...common.pagination import PageQuerySerializer
from ...common.serializers import AwareDateTimeField, StrictSerializer

MAX_INT = 2_147_483_647
MAX_IMAGES = 10
MAX_DEADLINE_HOURS = 168  # 申込の締め切りは最大で開催の7日前
# 生産者が自分で選べる公開状態（suspended は運営だけが付ける）
PRODUCER_PUBLISH_CHOICES = [PublishStatus.DRAFT, PublishStatus.PUBLIC, PublishStatus.PRIVATE]


# ============================================================
# 体験一覧・登録・詳細・更新
# ============================================================

class ExperienceListQuerySerializer(PageQuerySerializer):
    """GET /dashboard/experiences のクエリ。publishStatus 省略で全状態"""

    publish_status = serializers.ChoiceField(choices=PublishStatus.choices, required=False)


class ExperienceSummarySerializer(serializers.ModelSerializer):
    """体験一覧の1件。slot_count・application_count・next_start_at は view の annotate で付ける"""

    slot_count = serializers.IntegerField()
    application_count = serializers.IntegerField()
    next_start_at = serializers.DateTimeField(allow_null=True)

    class Meta:
        model = Experience
        fields = ["id", "title", "publish_status", "prefecture_id", "price_adult", "price_child",
                    "slot_count", "application_count", "next_start_at", "created_at", "updated_at"]


class FlowItemSerializer(StrictSerializer):
    """当日の流れの1行 {time: "10:00", text: "集合"}"""

    time = serializers.RegexField(r"^([01]\d|2[0-3]):[0-5]\d$", error_messages={
        "invalid": "時刻は HH:MM（例: 09:30）で入力してください。"})
    text = serializers.CharField(max_length=500)


class ExperienceWriteSerializer(StrictSerializer):
    """体験の登録（POST）・更新（PATCH、partial=True で使う）の入力

    - 文字列は前後の空白を除き、空白だけなら 400（DRF の CharField の初期設定）
    - prefecture_id は省略すると view で生産者の都道府県にする。存在しない ID は 400
    - imageKeys は自分がアップロードした画像のキー（最大10件・重複不可・配列の順が表示順）。送ったら全部置き換え
    - bookingDeadlineHours は申込・キャンセルの締め切り（開催の何時間前か、0〜168。省略時24）
    """

    title = serializers.CharField(max_length=100)
    prefecture_id = serializers.PrimaryKeyRelatedField(
        source="prefecture", queryset=Prefecture.objects.all(), required=False)
    description = serializers.CharField(max_length=10000)
    place = serializers.CharField(max_length=200)
    price_adult = serializers.IntegerField(min_value=0, max_value=MAX_INT)
    price_child = serializers.IntegerField(min_value=0, max_value=MAX_INT, required=False, allow_null=True)
    age_condition = serializers.CharField(max_length=50, required=False, allow_null=True, allow_blank=True)
    family_ok = serializers.BooleanField(required=False)
    beginner_ok = serializers.BooleanField(required=False)
    flow = serializers.ListField(child=FlowItemSerializer(), max_length=50, required=False, allow_null=True)
    belongings = serializers.ListField(child=serializers.CharField(max_length=500), max_length=50,
                                        required=False, allow_null=True)
    notes = serializers.ListField(child=serializers.CharField(max_length=500), max_length=50,
                                    required=False, allow_null=True)
    cancel_policy = serializers.CharField(max_length=10000)
    publish_status = serializers.ChoiceField(choices=PRODUCER_PUBLISH_CHOICES, required=False)
    booking_deadline_hours = serializers.IntegerField(min_value=0, max_value=MAX_DEADLINE_HOURS, required=False)
    image_keys = serializers.ListField(child=serializers.CharField(max_length=500), max_length=MAX_IMAGES,
                                       required=False)

    def validate_age_condition(self, value):
        return value or None  # 空文字は「条件なし」として null で保存する

    def validate_image_keys(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError("同じ画像を複数指定することはできません。")
        return value

    def validate(self, attrs):
        if self.partial and not self.initial_data:
            raise serializers.ValidationError("更新する項目を1つ以上指定してください。")
        return attrs


class ExperienceImageSerializer(serializers.Serializer):
    """体験画像 {id, imageKey, url, sortOrder}"""

    id = serializers.IntegerField()
    image_key = serializers.CharField(source="image.name")
    url = ImageUrlField(source="image")
    sort_order = serializers.IntegerField()


class ExperienceDetailSerializer(serializers.ModelSerializer):
    """体験詳細（編集画面用の全項目と画像）。予約枠は予約枠一覧APIで取る"""

    images = ExperienceImageSerializer(source="experience_images", many=True)

    class Meta:
        model = Experience
        fields = ["id", "producer_id", "title", "prefecture_id", "description", "place", "price_adult",
                    "price_child", "age_condition", "family_ok", "beginner_ok", "flow", "belongings", "notes",
                    "cancel_policy", "booking_deadline_hours", "publish_status", "images", "created_at",
                    "updated_at"]


class ExperienceWriteResponseSerializer(serializers.ModelSerializer):
    """登録・更新のレスポンス"""

    class Meta:
        model = Experience
        fields = ["id", "producer_id", "publish_status", "created_at", "updated_at"]


# ============================================================
# 体験申込者一覧
# ============================================================

class ApplicationQuerySerializer(PageQuerySerializer):
    status = serializers.ChoiceField(choices=Reservation.Status.choices, required=False)
    slot_id = serializers.IntegerField(min_value=1, required=False)


class ReservedSlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExperienceSlot
        fields = ["id", "start_at", "duration_min", "status"]


class ApplicationSerializer(serializers.ModelSerializer):
    """申込者1件。メールアドレス・生年月日・Stripe の ID は返さない。

    退会・停止済みの会員は氏名・代表者氏名・電話・メッセージを null にする（user.id と isActive=false は残す）。
    """

    slot = ReservedSlotSerializer()
    user = serializers.SerializerMethodField()

    class Meta:
        model = Reservation
        fields = ["id", "reservation_no", "slot", "user", "adult_count", "child_count", "infant_count",
                    "representative_name", "phone", "message", "total_amount", "status", "policy_agreed_at",
                    "created_at"]

    @staticmethod
    def _is_active(user):
        return user.is_active and user.deleted_at is None

    def get_user(self, obj):
        active = self._is_active(obj.user)
        return {
            "id": obj.user_id,
            "last_name": obj.user.last_name if active else None,
            "first_name": obj.user.first_name if active else None,
            "is_active": active,
        }

    def to_representation(self, obj):
        data = super().to_representation(obj)
        if not self._is_active(obj.user):
            for key in ("representative_name", "phone", "message"):
                data[key] = None
        return data


# ============================================================
# 予約枠
# ============================================================

class SlotQuerySerializer(PageQuerySerializer):
    status = serializers.ChoiceField(choices=ExperienceSlot.Status.choices, required=False)


class SlotSerializer(serializers.ModelSerializer):
    """予約枠。remainingCapacity は残りの人数（マイナスにはしない）"""

    remaining_capacity = serializers.SerializerMethodField()

    class Meta:
        model = ExperienceSlot
        fields = ["id", "experience_id", "start_at", "duration_min", "capacity", "status", "reserved_count",
                    "remaining_capacity", "created_at", "updated_at"]

    def get_remaining_capacity(self, obj):
        return max(obj.capacity - obj.reserved_count, 0)


def validate_future(value):
    if value <= timezone.now():
        raise serializers.ValidationError("開催日時は現在より後の日時を指定してください。")
    return value


class SlotCreateSerializer(StrictSerializer):
    """予約枠の登録。新しく作るときの状態は open か closed（省略で open）"""

    start_at = AwareDateTimeField(validators=[validate_future])
    duration_min = serializers.IntegerField(min_value=1, max_value=10080)
    capacity = serializers.IntegerField(min_value=1, max_value=MAX_INT)
    status = serializers.ChoiceField(
        choices=[ExperienceSlot.Status.OPEN, ExperienceSlot.Status.CLOSED], required=False,
        default=ExperienceSlot.Status.OPEN)


class SlotUpdateSerializer(StrictSerializer):
    """予約枠の更新・中止。送った項目だけ変える。canceled（中止）は他の項目と同時に送れない"""

    start_at = AwareDateTimeField(required=False, validators=[validate_future])
    duration_min = serializers.IntegerField(min_value=1, max_value=10080, required=False)
    capacity = serializers.IntegerField(min_value=1, max_value=MAX_INT, required=False)
    status = serializers.ChoiceField(choices=ExperienceSlot.Status.choices, required=False)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("更新する項目を1つ以上指定してください。")
        if attrs.get("status") == ExperienceSlot.Status.CANCELED and len(attrs) > 1:
            raise serializers.ValidationError({"status": ["中止するときは、ほかの項目を同時に変更できません。"]})
        return attrs
