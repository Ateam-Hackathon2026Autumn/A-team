"""生産者ダッシュボードの求人管理・採用のシリアライザー"""

from django.utils import timezone

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

    id = serializers.IntegerField(
        required=False,
        min_value=1,
        error_messages={
            "invalid": "勤務日IDは整数で指定してください。",
            "min_value": "勤務日IDが正しくありません。",
        },
    )

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
        max_value=1000000,
        error_messages={
            "invalid": "ページ番号は整数で指定してください。",
            "min_value": "ページ番号は1以上にしてください。",
            "max_value": "ページ番号が大きすぎます。",
        },
    )

    page_size = serializers.IntegerField(
        required=False,
        default=20,
        min_value=1,
        max_value=100,
        error_messages={
            "invalid": "1ページあたりの件数は整数で指定してください。",
            "min_value": "1ページあたりの件数は1以上にしてください。",
            "max_value": "1ページあたりの件数は100以下にしてください。",
        },
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
        error_messages={
            "max_length": "検索キーワードは100文字以内で入力してください。",
        },
    )

    publish_status = serializers.ChoiceField(
        required=False,
        choices=JOB_PUBLISH_STATUSES + ["suspended"],
        error_messages={
            "invalid_choice": "指定された掲載状態は正しくありません。",
        },
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
        error_messages={
            "invalid": "都道府県IDは整数で指定してください。",
            "min_value": "都道府県IDが正しくありません。",
        },
    )

    title = serializers.CharField(
        required=True,
        max_length=100,
        allow_blank=False,
        error_messages={
            "required": "求人タイトルは必須です。",
            "blank": "求人タイトルを入力してください。",
            "max_length": "求人タイトルは100文字以内で入力してください。",
        },
    )

    term_type = serializers.ChoiceField(
        required=True,
        choices=JOB_TERM_TYPES,
        error_messages={
            "required": "雇用期間の種類は必須です。",
            "invalid_choice": "雇用期間の種類が正しくありません。",
        },
    )

    pay_unit = serializers.ChoiceField(
        required=True,
        choices=JOB_PAY_UNITS,
        error_messages={
            "required": "給与単位は必須です。",
            "invalid_choice": "給与単位が正しくありません。",
        },
    )

    pay_amount = serializers.IntegerField(
        required=True,
        min_value=1,
        error_messages={
            "required": "給与金額は必須です。",
            "min_value": "給与金額は1以上にしてください。",
            "invalid": "給与金額は整数で入力してください。",
        },
    )

    period_start = serializers.DateField(
        required=False,
        allow_null=True,
        error_messages={
            "invalid": "募集開始日の形式が正しくありません。",
        },
    )

    period_end = serializers.DateField(
        required=False,
        allow_null=True,
        error_messages={
            "invalid": "募集終了日の形式が正しくありません。",
        },
    )

    work_hours = serializers.CharField(
        required=True,
        max_length=50,
        allow_blank=False,
        error_messages={
            "required": "勤務時間は必須です。",
            "blank": "勤務時間を入力してください。",
            "max_length": "勤務時間は50文字以内で入力してください。",
        },
    )

    work_place = serializers.CharField(
        required=True,
        max_length=200,
        allow_blank=False,
        error_messages={
            "required": "勤務地は必須です。",
            "blank": "勤務地を入力してください。",
            "max_length": "勤務地は200文字以内で入力してください。",
        },
    )

    slots = serializers.IntegerField(
        required=True,
        min_value=1,
        error_messages={
            "required": "募集人数は必須です。",
            "min_value": "募集人数は1人以上にしてください。",
            "invalid": "募集人数は整数で入力してください。",
        },
    )

    description = serializers.CharField(
        required=True,
        allow_blank=False,
        error_messages={
            "required": "求人詳細は必須です。",
            "blank": "求人詳細を入力してください。",
        },
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
        error_messages={
            "required": "未経験者の応募可否は必須です。",
            "invalid": "未経験者の応募可否は真偽値で指定してください。",
        },
    )

    # S3などにアップロード済みの画像キーを受け取る
    cover_image = serializers.CharField(
        required=False,
        allow_null=True,
        max_length=500,
        error_messages={
            "max_length": "画像のキーは500文字以内で指定してください。",
        },
    )

    publish_status = serializers.ChoiceField(
        required=False,
        choices=JOB_PUBLISH_STATUSES,
        default="draft",
        error_messages={
            "invalid_choice": "掲載状態が正しくありません。",
        },
    )

    work_dates = JobWorkDateSerializer(
        many=True,
        required=False,
        allow_empty=True,
    )

    def validate(self, attrs):
        """求人全体の入力を検証する"""

        instance = self.instance

        # 更新時は入力値がなければ既存値を使用する
        term_type = attrs.get(
            "term_type",
            instance.term_type if instance else None,
        )

        publish_status = attrs.get(
            "publish_status",
            instance.publish_status if instance else "draft",
        )

        period_start = attrs.get(
            "period_start",
            instance.period_start if instance else None,
        )

        period_end = attrs.get(
            "period_end",
            instance.period_end if instance else None,
        )

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

        # 勤務日の取得
        if "work_dates" in attrs:
            work_dates = attrs["work_dates"]
        elif instance:
            work_dates = list(
                instance.job_work_dates.all()
            )
        else:
            work_dates = []

        # 新規登録時は勤務日IDを指定できない
        if not instance and any(
            isinstance(item, dict) and "id" in item
            for item in work_dates
        ):
            raise serializers.ValidationError({
                "work_dates": [
                    "新規登録時に勤務日IDは指定できません。"
                ]
            })

        # 更新時の勤務日IDを検証
        if instance and "work_dates" in attrs:
            work_date_ids = [
                item["id"]
                for item in work_dates
                if "id" in item
            ]

            # 同じIDの重複指定を禁止
            if len(work_date_ids) != len(set(work_date_ids)):
                raise serializers.ValidationError({
                    "work_dates": [
                        "同じ勤務日IDを複数指定することはできません。"
                    ]
                })

            # 指定された勤務日IDがこの求人に属しているか確認
            existing_count = instance.job_work_dates.filter(
                id__in=work_date_ids
            ).count()

            if existing_count != len(work_date_ids):
                raise serializers.ValidationError({
                    "work_dates": [
                        "指定された勤務日がこの求人に存在しません。"
                    ]
                })

        # 長期求人には勤務日を登録できない
        if term_type == "long" and work_dates:
            raise serializers.ValidationError({
                "work_dates": [
                    "長期求人には勤務日を登録できません。"
                ]
            })

        # 勤務日の重複チェック
        dates = [
            item["work_date"]
            if isinstance(item, dict)
            else item.work_date
            for item in work_dates
        ]

        if len(dates) != len(set(dates)):
            raise serializers.ValidationError({
                "work_dates": [
                    "同じ勤務日を重複して登録することはできません。"
                ]
            })

        # 単発・短期の公開求人には今日以降の勤務日が必要
        if (
            term_type in ["one_day", "short"]
            and publish_status == "public"
        ):
            today = timezone.localdate()

            future_dates = [
                work_date
                for work_date in dates
                if work_date >= today
            ]

            if not future_dates:
                raise serializers.ValidationError({
                    "work_dates": [
                        "公開する単発・短期求人には今日以降の勤務日を1日以上登録してください。"
                    ]
                })

        # 勤務日が募集期間内か確認
        for index, item in enumerate(work_dates):
            work_date = (
                item["work_date"]
                if isinstance(item, dict)
                else item.work_date
            )

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
        source="job_work_dates",
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
        error_messages={
            "invalid": "都道府県IDは整数で指定してください。",
            "min_value": "都道府県IDが正しくありません。",
        },
    )

    title = serializers.CharField(
        required=False,
        max_length=100,
        allow_blank=False,
        error_messages={
            "blank": "求人タイトルを入力してください。",
            "max_length": "求人タイトルは100文字以内で入力してください。",
        },
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


# ============================================================
# 求人削除
# DELETE /api/v1/dashboard/jobs/:jobId
# ============================================================

class JobDeleteSerializer(StrictSerializer):
    """求人削除時のIDを検証する"""

    job_id = serializers.IntegerField(
        required=True,
        min_value=1,
        error_messages={
            "required": "求人IDは必須です。",
            "invalid": "求人IDは整数で指定してください。",
            "min_value": "求人IDが正しくありません。",
        },
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
        error_messages={
            "invalid_choice": "応募状態が正しくありません。",
        },
    )


class JobApplicationSerializer(serializers.Serializer):
    """応募者情報のレスポンス"""

    id = serializers.IntegerField()

    user_id = serializers.IntegerField()

    last_name = serializers.CharField(
        source="user.last_name",
    )

    first_name = serializers.CharField(
        source="user.first_name",
    )

    phone = serializers.CharField(
        source="user.phone",
        allow_null=True,
        allow_blank=True,
    )

    age = serializers.SerializerMethodField()

    message = serializers.CharField(
        allow_null=True,
    )

    answers = serializers.JSONField(
        allow_null=True,
    )

    work_dates = serializers.SerializerMethodField()

    status = serializers.ChoiceField(
        choices=APPLICATION_STATUSES,
    )

    decided_at = serializers.DateTimeField(
        allow_null=True,
    )

    created_at = serializers.DateTimeField()

    updated_at = serializers.DateTimeField()

    def get_age(self, obj):
        """生年月日から現在の年齢を計算する"""

        birth_date = obj.user.birth_date

        if not birth_date:
            return None

        today = timezone.localdate()

        age = today.year - birth_date.year

        if (
            today.month,
            today.day
        ) < (
            birth_date.month,
            birth_date.day
        ):
            age -= 1

        return age

    def get_work_dates(self, obj):
        """応募者が希望した勤務日を返す"""

        return [
            {
                "id": item.work_date_id,
                "work_date": item.work_date.work_date,
            }
            for item in obj.application_work_dates.select_related(
                "work_date"
            ).all()
        ]


# ============================================================
# 採用・不採用
# PATCH /api/v1/dashboard/jobs/:jobId/applications/:applicationId
# ============================================================

class JobApplicationStatusUpdateSerializer(StrictSerializer):
    """応募者の状態変更を検証する"""

    status = serializers.ChoiceField(
        required=True,
        choices=[
            "screening",
            "hired",
            "rejected",
            "completed",
        ],
        error_messages={
            "required": "応募状態を指定してください。",
            "invalid_choice": "指定された応募状態は正しくありません。",
        },
    )