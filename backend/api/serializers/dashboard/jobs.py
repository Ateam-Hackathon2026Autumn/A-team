"""生産者ダッシュボードの求人管理・採用のシリアライザー"""


from rest_framework import serializers

from api.common.serializers import StrictSerializer


# ============================================================
# 共通設定
# ============================================================

JOB_TERM_TYPES = [
    "one_day",
    "short",
    "long",
]

JOB_PAY_UNITS = [
    "hourly",
    "daily",
    "monthly",
]

JOB_PUBLISH_STATUSES = [
    "draft",
    "public",
    "private",
]

APPLICATION_STATUSES = [
    "applied",
    "screening",
    "hired",
    "rejected",
    "withdrawn",
    "completed",
]


# ============================================================
# 勤務日
# job_work_dates
# ============================================================

class JobWorkDateSerializer(StrictSerializer):
    """求人の勤務日を検証する"""

    work_date = serializers.DateField(
        required=True,
        error_messages={
            "required": "勤務日は必須です。",
            "invalid": "勤務日の形式が正しくありません。",
        },
    )

    needed_count = serializers.IntegerField(
        required=True,
        min_value=1,
        error_messages={
            "required": "募集人数は必須です。",
            "min_value": "募集人数は1人以上にしてください。",
            "invalid": "募集人数は整数で入力してください。",
        },
    )


# ============================================================
# ページネーション共通
# ============================================================

class DashboardPaginationQuerySerializer(StrictSerializer):
    """一覧APIのページネーションを検証する"""

    page = serializers.IntegerField(
        required=False,
        default=1,
        min_value=1,
    )

    page_size = serializers.IntegerField(
        required=False,
        default=20,
        min_value=1,
        max_value=100,
    )


# ============================================================
# 求人一覧
# GET /api/v1/dashboard/jobs
# ============================================================

class JobListQuerySerializer(DashboardPaginationQuerySerializer):
    """求人一覧の検索条件を検証する"""

    keyword = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=100,
    )

    publish_status = serializers.ChoiceField(
        required=False,
        choices=JOB_PUBLISH_STATUSES + ["suspended"],
    )


class JobListSerializer(serializers.Serializer):
    """求人一覧のレスポンス"""

    id = serializers.IntegerField()

    title = serializers.CharField()

    term_type = serializers.CharField()

    pay_unit = serializers.CharField()

    pay_amount = serializers.IntegerField()

    period_start = serializers.DateField(
        allow_null=True,
    )

    period_end = serializers.DateField(
        allow_null=True,
    )

    work_hours = serializers.CharField()

    work_place = serializers.CharField()

    slots = serializers.IntegerField()

    inexperienced_ok = serializers.BooleanField()

    cover_image = serializers.CharField(
        allow_null=True,
    )

    publish_status = serializers.CharField()

    created_at = serializers.DateTimeField()

    updated_at = serializers.DateTimeField()


# ============================================================
# 求人登録
# POST /api/v1/dashboard/jobs
# ============================================================

class JobCreateSerializer(StrictSerializer):
    """求人登録の入力を検証する"""

    prefecture_id = serializers.IntegerField(
        required=False,
        min_value=1,
    )

    title = serializers.CharField(
        required=True,
        max_length=100,
        allow_blank=False,
    )

    term_type = serializers.ChoiceField(
        required=True,
        choices=JOB_TERM_TYPES,
    )

    pay_unit = serializers.ChoiceField(
        required=True,
        choices=JOB_PAY_UNITS,
    )

    pay_amount = serializers.IntegerField(
        required=True,
        min_value=1,
    )

    period_start = serializers.DateField(
        required=False,
        allow_null=True,
    )

    period_end = serializers.DateField(
        required=False,
        allow_null=True,
    )

    work_hours = serializers.CharField(
        required=True,
        max_length=50,
        allow_blank=False,
    )

    work_place = serializers.CharField(
        required=True,
        max_length=200,
        allow_blank=False,
    )

    slots = serializers.IntegerField(
        required=True,
        min_value=1,
    )

    description = serializers.CharField(
        required=True,
        allow_blank=False,
    )

    requirements = serializers.JSONField(
        required=False,
        allow_null=True,
    )

    belongings = serializers.JSONField(
        required=False,
        allow_null=True,
    )

    notes = serializers.JSONField(
        required=False,
        allow_null=True,
    )

    inexperienced_ok = serializers.BooleanField(
        required=True,
    )

    cover_image = serializers.CharField(
        required=False,
        allow_null=True,
        max_length=500,
    )

    publish_status = serializers.ChoiceField(
        required=False,
        choices=JOB_PUBLISH_STATUSES,
        default="draft",
    )

    work_dates = JobWorkDateSerializer(
        many=True,
        required=False,
        allow_empty=True,
    )

    def validate(self, attrs):
        """求人全体の入力を検証する"""

        period_start = attrs.get("period_start")
        period_end = attrs.get("period_end")

        # 募集開始日と終了日の前後関係
        if (
            period_start
            and period_end
            and period_start > period_end
        ):
            raise serializers.ValidationError({
                "period_end": [
                    "募集終了日は募集開始日以降にしてください。"
                ]
            })

        # 勤務日の重複チェック
        work_dates = attrs.get("work_dates", [])

        dates = [
            item["work_date"]
            for item in work_dates
        ]

        if len(dates) != len(set(dates)):
            raise serializers.ValidationError({
                "work_dates": [
                    "同じ勤務日を重複して登録することはできません。"
                ]
            })

        # 勤務日が募集期間内か確認
        for index, item in enumerate(work_dates):
            work_date = item["work_date"]

            if period_start and work_date < period_start:
                raise serializers.ValidationError({
                    "work_dates": {
                        index: {
                            "work_date": [
                                "勤務日は募集開始日以降にしてください。"
                            ]
                        }
                    }
                })

            if period_end and work_date > period_end:
                raise serializers.ValidationError({
                    "work_dates": {
                        index: {
                            "work_date": [
                                "勤務日は募集終了日以前にしてください。"
                            ]
                        }
                    }
                })

        return attrs


# ============================================================
# 求人詳細
# GET /api/v1/dashboard/jobs/:jobId
# ============================================================

class JobDetailSerializer(JobListSerializer):
    """求人詳細のレスポンス"""

    prefecture_id = serializers.IntegerField()

    description = serializers.CharField()

    requirements = serializers.JSONField(
        allow_null=True,
    )

    belongings = serializers.JSONField(
        allow_null=True,
    )

    notes = serializers.JSONField(
        allow_null=True,
    )

    work_dates = JobWorkDateSerializer(
        many=True,
    )


# ============================================================
# 求人更新
# PATCH /api/v1/dashboard/jobs/:jobId
# ============================================================

class JobUpdateSerializer(JobCreateSerializer):
    """求人更新の入力を検証する"""

    prefecture_id = serializers.IntegerField(
        required=False,
        min_value=1,
    )

    title = serializers.CharField(
        required=False,
        max_length=100,
        allow_blank=False,
    )

    term_type = serializers.ChoiceField(
        required=False,
        choices=JOB_TERM_TYPES,
    )

    pay_unit = serializers.ChoiceField(
        required=False,
        choices=JOB_PAY_UNITS,
    )

    pay_amount = serializers.IntegerField(
        required=False,
        min_value=1,
    )

    work_hours = serializers.CharField(
        required=False,
        max_length=50,
        allow_blank=False,
    )

    work_place = serializers.CharField(
        required=False,
        max_length=200,
        allow_blank=False,
    )

    slots = serializers.IntegerField(
        required=False,
        min_value=1,
    )

    description = serializers.CharField(
        required=False,
        allow_blank=False,
    )

    inexperienced_ok = serializers.BooleanField(
        required=False,
    )

    publish_status = serializers.ChoiceField(
        required=False,
        choices=JOB_PUBLISH_STATUSES,
    )

    def validate(self, attrs):
        """更新時の入力を検証する"""

        attrs = super().validate(attrs)

        instance = self.instance

        # 更新時は既存値と合わせて募集期間を検証
        if instance:
            period_start = attrs.get(
                "period_start",
                instance.period_start,
            )

            period_end = attrs.get(
                "period_end",
                instance.period_end,
            )

            if (
                period_start
                and period_end
                and period_start > period_end
            ):
                raise serializers.ValidationError({
                    "period_end": [
                        "募集終了日は募集開始日以降にしてください。"
                    ]
                })

        return attrs


# ============================================================
# 求人削除
# DELETE /api/v1/dashboard/jobs/:jobId
# ============================================================

class JobDeleteSerializer(StrictSerializer):
    """求人削除時のIDを検証する"""

    job_id = serializers.IntegerField(
        required=True,
        min_value=1,
    )


# ============================================================
# 応募者一覧
# GET /api/v1/dashboard/jobs/:jobId/applications
# ============================================================

class JobApplicationListQuerySerializer(
    DashboardPaginationQuerySerializer
):
    """応募者一覧の検索条件を検証する"""

    status = serializers.ChoiceField(
        required=False,
        choices=APPLICATION_STATUSES,
    )


class JobApplicationSerializer(serializers.Serializer):
    """応募者情報のレスポンス"""

    id = serializers.IntegerField()

    user_id = serializers.IntegerField()

    last_name = serializers.CharField()

    first_name = serializers.CharField()

    message = serializers.CharField(
        allow_null=True,
    )

    answers = serializers.JSONField(
        allow_null=True,
    )

    status = serializers.ChoiceField(
        choices=APPLICATION_STATUSES,
    )

    decided_at = serializers.DateTimeField(
        allow_null=True,
    )

    created_at = serializers.DateTimeField()

    updated_at = serializers.DateTimeField()


# ============================================================
# 採用・不採用
# PATCH /api/v1/dashboard/jobs/:jobId/applications/:applicationId
# ============================================================

class JobApplicationStatusUpdateSerializer(StrictSerializer):
    """応募者の採用・不採用を検証する"""

    status = serializers.ChoiceField(
        required=True,
        choices=[
            "hired",
            "rejected",
        ],
        error_messages={
            "required": "採用・不採用の状態を指定してください。",
            "invalid_choice": "採用または不採用を指定してください。",
        },
    )



# """求人管理・採用 のシリアライザー

# 使う view: api/views/dashboard/jobs.py

# このファイルに書くもの（リクエストの検証用・レスポンスの形用）:
#   - 求人一覧（生産者）（GET /api/v1/dashboard/jobs）: クエリ・入力の検証とレスポンス
#   - 求人登録（POST /api/v1/dashboard/jobs）: 入力の検証とレスポンス
#   - 求人詳細（生産者）（GET /api/v1/dashboard/jobs/:jobId）: クエリ・入力の検証とレスポンス
#   - 求人更新（PATCH /api/v1/dashboard/jobs/:jobId）: 入力の検証とレスポンス
#   - 求人削除（DELETE /api/v1/dashboard/jobs/:jobId）: 入力の検証とレスポンス
#   - 求人応募者一覧（GET /api/v1/dashboard/jobs/:jobId/applications）: クエリ・入力の検証とレスポンス
#   - 採用・不採用（PATCH /api/v1/dashboard/jobs/:jobId/applications/:applicationId）: 入力の検証とレスポンス

# 入力エラーは 400（項目ごとのメッセージ）。カラム名は claude/er-diagram.md に合わせる
# """
