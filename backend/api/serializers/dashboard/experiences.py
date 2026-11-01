from rest_framework import serializers

# ============================================================
# 共通設定
# ============================================================

PUBLISH_STATUS_CHOICES = (
    "draft",
    "public",
    "private",
    "suspended",
)

SLOT_STATUS_CHOICES = (
    "open",
    "closed",
    "canceled",
)

RESERVATION_STATUS_CHOICES = (
    "applied",
    "confirmed",
    "canceled",
    "attended",
)

# ============================================================
# 共通バリデーション
# ============================================================

class DashboardPaginationSerializer(serializers.Serializer):
    """一覧APIのページネーション用クエリ。"""

    page = serializers.IntegerField(
        required=False,
        default=1,
        min_value=1,
        error_messages={
            "invalid": "ページ番号は整数で指定してください。",
            "min_value": "ページ番号は1以上で指定してください。",
        },
    )

    page_size = serializers.IntegerField(
        required=False,
        default=20,
        min_value=1,
        max_value=100,
        error_messages={
            "invalid": "1ページあたりの件数は整数で指定してください。",
            "min_value": "1ページあたりの件数は1以上で指定してください。",
            "max_value": "1ページあたりの件数は100以下で指定してください。",
        },
    )

class DashboardExperienceIdSerializer(serializers.Serializer):
    """体験IDの検証。"""

    experience_id = serializers.IntegerField(
        min_value=1,
        error_messages={
            "required": "体験IDは必須です。",
            "invalid": "体験IDは整数で指定してください。",
            "min_value": "体験IDは1以上で指定してください。",
        },
    )

class DashboardExperienceSlotIdSerializer(serializers.Serializer):
    """予約枠IDの検証。"""

    slot_id = serializers.IntegerField(
        min_value=1,
        error_messages={
            "required": "予約枠IDは必須です。",
            "invalid": "予約枠IDは整数で指定してください。",
            "min_value": "予約枠IDは1以上で指定してください。",
        },
    )

# ============================================================
# 体験一覧
# GET /api/v1/dashboard/experiences
# ============================================================

class DashboardExperienceListQuerySerializer(
    DashboardPaginationSerializer
):
    """体験一覧のクエリパラメータ。"""

    search = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=100,
        error_messages={
            "max_length": "検索キーワードは100文字以内で入力してください。",
        },
    )

    publish_status = serializers.ChoiceField(
        required=False,
        choices=PUBLISH_STATUS_CHOICES,
        error_messages={
            "invalid_choice": (
                "公開状態は draft、public、private、suspended の"
                "いずれかを指定してください。"
            ),
        },
    )

class DashboardExperienceImageSerializer(serializers.Serializer):
    """体験画像のレスポンス。"""

    id = serializers.IntegerField(read_only=True)
    image = serializers.CharField(read_only=True)
    sort_order = serializers.IntegerField(read_only=True)

class DashboardExperienceSlotSummarySerializer(serializers.Serializer):
    """体験に関連する開催日程のレスポンス。"""

    id = serializers.IntegerField(read_only=True)
    start_at = serializers.DateTimeField(read_only=True)
    duration_min = serializers.IntegerField(read_only=True)
    capacity = serializers.IntegerField(read_only=True)
    reserved_count = serializers.IntegerField(read_only=True)
    status = serializers.CharField(read_only=True)

class DashboardExperienceResponseSerializer(serializers.Serializer):
    """体験情報のレスポンス形式。

    ER図の experiences テーブルに対応する。
    """

    id = serializers.IntegerField(read_only=True)
    producer_id = serializers.IntegerField(read_only=True)
    prefecture_id = serializers.IntegerField(read_only=True)

    title = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)
    place = serializers.CharField(read_only=True)

    price_adult = serializers.IntegerField(read_only=True)
    price_child = serializers.IntegerField(
        read_only=True,
        allow_null=True,
    )

    age_condition = serializers.CharField(
        read_only=True,
        allow_null=True,
    )

    family_ok = serializers.BooleanField(read_only=True)
    beginner_ok = serializers.BooleanField(read_only=True)

    flow = serializers.JSONField(read_only=True, allow_null=True)
    belongings = serializers.JSONField(read_only=True, allow_null=True)
    notes = serializers.JSONField(read_only=True, allow_null=True)

    cancel_policy = serializers.CharField(read_only=True)
    publish_status = serializers.CharField(read_only=True)

    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    images = DashboardExperienceImageSerializer(
        many=True,
        read_only=True,
    )

    slots = DashboardExperienceSlotSummarySerializer(
        many=True,
        read_only=True,
    )

class DashboardExperienceListResponseSerializer(serializers.Serializer):
    """体験一覧のレスポンス。"""

    results = DashboardExperienceResponseSerializer(many=True)
    total = serializers.IntegerField(min_value=0)
    page = serializers.IntegerField(min_value=1)
    page_size = serializers.IntegerField(min_value=1)

# ============================================================
# 体験登録
# POST /api/v1/dashboard/experiences
# ============================================================

class DashboardExperienceCreateSerializer(serializers.Serializer):
    """体験登録時の入力検証。"""

    prefecture_id = serializers.IntegerField(
        required=False,
        min_value=1,
        error_messages={
            "required": "開催地の都道府県を指定してください。",
            "invalid": "都道府県IDは整数で指定してください。",
            "min_value": "都道府県IDは1以上で指定してください。",
        },
    )

    title = serializers.CharField(
        max_length=100,
        error_messages={
            "required": "体験タイトルを入力してください。",
            "blank": "体験タイトルを入力してください。",
            "max_length": "体験タイトルは100文字以内で入力してください。",
        },
    )

    description = serializers.CharField(
        error_messages={
            "required": "体験内容を入力してください。",
            "blank": "体験内容を入力してください。",
        },
    )

    place = serializers.CharField(
        max_length=200,
        error_messages={
            "required": "開催場所・集合場所を入力してください。",
            "blank": "開催場所・集合場所を入力してください。",
            "max_length": "開催場所は200文字以内で入力してください。",
        },
    )

    price_adult = serializers.IntegerField(
        min_value=0,
        error_messages={
            "required": "大人1名の料金を入力してください。",
            "invalid": "大人料金は整数で入力してください。",
            "min_value": "大人料金は0円以上で指定してください。",
        },
    )

    price_child = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=0,
        error_messages={
            "invalid": "子ども料金は整数で入力してください。",
            "min_value": "子ども料金は0円以上で指定してください。",
        },
    )

    age_condition = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        max_length=50,
        error_messages={
            "max_length": "年齢条件は50文字以内で入力してください。",
        },
    )

    family_ok = serializers.BooleanField(
        required=False,
        default=False,
        error_messages={
            "required": "親子参加の可否を指定してください。",
            "invalid": "親子参加の可否は真偽値で指定してください。",
        },
    )

    beginner_ok = serializers.BooleanField(
        required=False,
        default=False,
        error_messages={
            "required": "初心者歓迎の可否を指定してください。",
            "invalid": "初心者歓迎の可否は真偽値で指定してください。",
        },
    )

    flow = serializers.JSONField(
        required=False,
        allow_null=True,
        error_messages={
            "invalid": "当日の流れはJSON形式で指定してください。",
        },
    )

    belongings = serializers.JSONField(
        required=False,
        allow_null=True,
        error_messages={
            "invalid": "持ち物はJSON形式で指定してください。",
        },
    )

    notes = serializers.JSONField(
        required=False,
        allow_null=True,
        error_messages={
            "invalid": "注意事項はJSON形式で指定してください。",
        },
    )

    cancel_policy = serializers.CharField(
        error_messages={
            "required": "キャンセルポリシーを入力してください。",
            "blank": "キャンセルポリシーを入力してください。",
        },
    )

    publish_status = serializers.ChoiceField(
        required=False,
        default="draft",
        choices=PUBLISH_STATUS_CHOICES,
        error_messages={
            "invalid_choice": (
                "公開状態は draft、public、private、suspended の"
                "いずれかを指定してください。"
            ),
        },
    )

    def validate_title(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "体験タイトルを入力してください。"
            )

        return value

    def validate_description(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "体験内容を入力してください。"
            )

        return value

    def validate_place(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "開催場所・集合場所を入力してください。"
            )

        return value

    def validate_cancel_policy(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "キャンセルポリシーを入力してください。"
            )

        return value

    def validate_flow(self, value):
        if value is not None and not isinstance(value, list):
            raise serializers.ValidationError(
                "当日の流れは配列形式で指定してください。"
            )

        if value is not None:
            for index, item in enumerate(value):
                if not isinstance(item, dict):
                    raise serializers.ValidationError(
                        f"当日の流れの{index + 1}件目はオブジェクト形式で"
                        "指定してください。"
                    )

                if "time" not in item or "text" not in item:
                    raise serializers.ValidationError(
                        f"当日の流れの{index + 1}件目には"
                        "time と text が必要です。"
                    )

        return value

    def validate_belongings(self, value):
        if value is not None and not isinstance(value, list):
            raise serializers.ValidationError(
                "持ち物は配列形式で指定してください。"
            )

        return value

    def validate_notes(self, value):
        if value is not None and not isinstance(value, list):
            raise serializers.ValidationError(
                "注意事項は配列形式で指定してください。"
            )

        return value

# ============================================================
# 体験更新
# PATCH /api/v1/dashboard/experiences/:experienceId
# ============================================================

class DashboardExperienceUpdateSerializer(
    DashboardExperienceCreateSerializer
):
    """体験更新時の入力検証。

    PATCHなので全項目を必須にはしない。
    """

    prefecture_id = serializers.IntegerField(
        required=False,
        min_value=1,
        error_messages={
            "invalid": "都道府県IDは整数で指定してください。",
            "min_value": "都道府県IDは1以上で指定してください。",
        },
    )

    title = serializers.CharField(
        required=False,
        max_length=100,
        error_messages={
            "blank": "体験タイトルを入力してください。",
            "max_length": "体験タイトルは100文字以内で入力してください。",
        },
    )

    description = serializers.CharField(
        required=False,
        error_messages={
            "blank": "体験内容を入力してください。",
        },
    )

    place = serializers.CharField(
        required=False,
        max_length=200,
        error_messages={
            "blank": "開催場所・集合場所を入力してください。",
            "max_length": "開催場所は200文字以内で入力してください。",
        },
    )

    price_adult = serializers.IntegerField(
        required=False,
        min_value=0,
        error_messages={
            "invalid": "大人料金は整数で入力してください。",
            "min_value": "大人料金は0円以上で指定してください。",
        },
    )

    cancel_policy = serializers.CharField(
        required=False,
        error_messages={
            "blank": "キャンセルポリシーを入力してください。",
        },
    )

# ============================================================
# 体験削除
# DELETE /api/v1/dashboard/experiences/:experienceId
# ============================================================

class DashboardExperienceDeleteResponseSerializer(serializers.Serializer):
    """体験削除のレスポンス。"""

    message = serializers.CharField()

# ============================================================
# 体験申込者一覧
# GET /api/v1/dashboard/experiences/:experienceId/applications
# ============================================================

class DashboardExperienceApplicationQuerySerializer(
    DashboardPaginationSerializer
):

    slot_id = serializers.IntegerField(
        required=False,
        min_value=1,
        error_messages={
            "invalid": "予約枠IDは整数で指定してください。",
            "min_value": "予約枠IDは1以上で指定してください。",
        },
    )
    
    """体験申込者一覧のクエリ検証。"""

    status = serializers.ChoiceField(
        required=False,
        choices=RESERVATION_STATUS_CHOICES,
        error_messages={
            "invalid_choice": (
                "予約状況は applied、confirmed、canceled、attended の"
                "いずれかを指定してください。"
            ),
        },
    )

class DashboardExperienceApplicationResponseSerializer(
    serializers.Serializer
):
    """申込者1件分のレスポンス。

    reservations と users をJOINして取得したデータを想定する。
    """

    id = serializers.IntegerField(read_only=True)
    reservation_no = serializers.CharField(read_only=True)
    slot_id = serializers.IntegerField(read_only=True)
    user_id = serializers.IntegerField(read_only=True)

    adult_count = serializers.IntegerField(read_only=True)
    child_count = serializers.IntegerField(read_only=True)
    infant_count = serializers.IntegerField(read_only=True)

    representative_name = serializers.CharField(read_only=True)
    phone = serializers.CharField(read_only=True)
    message = serializers.CharField(read_only=True, allow_null=True)

    total_amount = serializers.IntegerField(read_only=True)
    status = serializers.CharField(read_only=True)
    policy_agreed_at = serializers.DateTimeField(read_only=True)

    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

class DashboardExperienceApplicationListResponseSerializer(
    serializers.Serializer
):
    """体験申込者一覧のレスポンス。"""

    results = DashboardExperienceApplicationResponseSerializer(many=True)
    total = serializers.IntegerField(min_value=0)
    page = serializers.IntegerField(min_value=1)
    page_size = serializers.IntegerField(min_value=1)

# ============================================================
# 予約枠一覧
# GET /api/v1/dashboard/experiences/:experienceId/slots
# ============================================================

class DashboardExperienceSlotQuerySerializer(
    DashboardPaginationSerializer
):
    """予約枠一覧のクエリ検証。"""

    status = serializers.ChoiceField(
        required=False,
        choices=SLOT_STATUS_CHOICES,
        error_messages={
            "invalid_choice": (
                "予約枠の状態は open、closed、canceled の"
                "いずれかを指定してください。"
            ),
        },
    )

class DashboardExperienceSlotResponseSerializer(serializers.Serializer):
    """開催日程・予約枠のレスポンス。"""

    id = serializers.IntegerField(read_only=True)
    experience_id = serializers.IntegerField(read_only=True)

    start_at = serializers.DateTimeField(read_only=True)
    duration_min = serializers.IntegerField(read_only=True)
    capacity = serializers.IntegerField(read_only=True)
    reserved_count = serializers.IntegerField(read_only=True)

    status = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

class DashboardExperienceSlotListResponseSerializer(
    serializers.Serializer
):
    """予約枠一覧のレスポンス。"""

    results = DashboardExperienceSlotResponseSerializer(many=True)
    total = serializers.IntegerField(min_value=0)
    page = serializers.IntegerField(min_value=1)
    page_size = serializers.IntegerField(min_value=1)

# ============================================================
# 予約枠登録
# POST /api/v1/dashboard/experiences/:experienceId/slots
# ============================================================

class DashboardExperienceSlotCreateSerializer(serializers.Serializer):
    """開催日程・予約枠の登録時の入力検証。"""

    start_at = serializers.DateTimeField(
        error_messages={
            "required": "開催日時を入力してください。",
            "invalid": "開催日時は正しい日時形式で指定してください。",
        },
    )

    duration_min = serializers.IntegerField(
        min_value=1,
        error_messages={
            "required": "所要時間を入力してください。",
            "invalid": "所要時間は整数で入力してください。",
            "min_value": "所要時間は1分以上で指定してください。",
        },
    )

    capacity = serializers.IntegerField(
        min_value=1,
        error_messages={
            "required": "定員を入力してください。",
            "invalid": "定員は整数で入力してください。",
            "min_value": "定員は1人以上で指定してください。",
        },
    )

    status = serializers.ChoiceField(
        required=False,
        default="open",
        choices=SLOT_STATUS_CHOICES,
        error_messages={
            "invalid_choice": (
                "予約枠の状態は open、closed、canceled の"
                "いずれかを指定してください。"
            ),
        },
    )

    def validate_start_at(self, value):
        from django.utils import timezone

        if value <= timezone.now():
            raise serializers.ValidationError(
                "開催日時は現在より後の日時を指定してください。"
            )

        return value

    def validate(self, attrs):
        # reserved_count は登録時にクライアントから受け取らない。
        # DBの初期値としてView側で0を設定する。
        return attrs

# ============================================================
# 予約枠更新・中止
# PATCH /api/v1/dashboard/experiences/:experienceId/slots/:slotId
# ============================================================

class DashboardExperienceSlotUpdateSerializer(
    serializers.Serializer
):
    """開催日程・予約枠の更新時の入力検証。"""

    start_at = serializers.DateTimeField(
        required=False,
        error_messages={
            "invalid": "開催日時は正しい日時形式で指定してください。",
        },
    )

    duration_min = serializers.IntegerField(
        required=False,
        min_value=1,
        error_messages={
            "invalid": "所要時間は整数で入力してください。",
            "min_value": "所要時間は1分以上で指定してください。",
        },
    )

    capacity = serializers.IntegerField(
        required=False,
        min_value=1,
        error_messages={
            "invalid": "定員は整数で入力してください。",
            "min_value": "定員は1人以上で指定してください。",
        },
    )

    status = serializers.ChoiceField(
        required=False,
        choices=SLOT_STATUS_CHOICES,
        error_messages={
            "invalid_choice": (
                "予約枠の状態は open、closed、canceled の"
                "いずれかを指定してください。"
            ),
        },
    )

    def validate_start_at(self, value):
        from django.utils import timezone

        if value <= timezone.now():
            raise serializers.ValidationError(
                "開催日時は現在より後の日時を指定してください。"
            )

        return value

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError(
                "更新する項目を1つ以上指定してください。"
            )

        return attrs

class DashboardExperienceSlotDeleteResponseSerializer(
    serializers.Serializer
):
    """予約枠削除のレスポンス。"""

    message = serializers.CharField()

# """体験管理・予約枠・申込者 のシリアライザー

# 使う view: api/views/dashboard/experiences.py

# このファイルに書くもの（リクエストの検証用・レスポンスの形用）:
#   - 体験一覧（生産者）（GET /api/v1/dashboard/experiences）: クエリ・入力の検証とレスポンス
#   - 体験登録（POST /api/v1/dashboard/experiences）: 入力の検証とレスポンス
#   - 体験詳細（生産者）（GET /api/v1/dashboard/experiences/:experienceId）: クエリ・入力の検証とレスポンス
#   - 体験更新（PATCH /api/v1/dashboard/experiences/:experienceId）: 入力の検証とレスポンス
#   - 体験削除（DELETE /api/v1/dashboard/experiences/:experienceId）: 入力の検証とレスポンス
#   - 体験申込者一覧（GET /api/v1/dashboard/experiences/:experienceId/applications）: クエリ・入力の検証とレスポンス
#   - 予約枠一覧（GET /api/v1/dashboard/experiences/:experienceId/slots）: クエリ・入力の検証とレスポンス
#   - 予約枠登録（POST /api/v1/dashboard/experiences/:experienceId/slots）: 入力の検証とレスポンス
#   - 予約枠更新・中止（PATCH /api/v1/dashboard/experiences/:experienceId/slots/:slotId）: 入力の検証とレスポンス
#   - 予約枠削除（DELETE /api/v1/dashboard/experiences/:experienceId/slots/:slotId）: 入力の検証とレスポンス

# 入力エラーは 400（項目ごとのメッセージ）。カラム名は claude/er-diagram.md に合わせる
# """

