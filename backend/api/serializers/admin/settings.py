"""お知らせ・管理者アカウント・操作ログ・分析（運営） のシリアライザー

使う view: api/views/admin/announcements.py・admins.py・audit_logs.py・analytics.py

  - お知らせ: AnnouncementListQuerySerializer {status, audience, keyword, page, pageSize}・AnnouncementWriteSerializer
      {title, body, audience, publishedAt}（作成は全部必須・publishedAt は null で下書き。更新は送った項目だけ）・
      AdminAnnouncementSerializer {id, title, audience, status, publishedAt, createdAt, updatedAt}（詳細は＋body）
  - 管理者アカウント: AdminCreateSerializer {email, lastName, firstName, groups}・AdminGroupsSerializer {groups}・
      StaffSerializer {id, email, name, groups, lastLogin, dateJoined, passwordSet}
  - 操作ログ: AuditLogQuerySerializer {adminId, action, targetType, targetId, startDate, endDate, page, pageSize}・
      AuditLogSerializer {id, admin {id, name}, action, targetType, targetId, detail, createdAt}
  - 分析: AnalyticsQuerySerializer {year}

入力エラーは 400（項目ごとのメッセージ）。カラム名は claude/er-diagram.md に合わせる
"""
from django.utils import timezone
from rest_framework import serializers

from marche.models import AuditLog, Notice, User

from ...common.pagination import PageQuerySerializer
from ...common.serializers import QuerySerializer, StrictSerializer
from ...services.staff import STAFF_GROUPS

MAX_ID = 2 ** 63 - 1
DRAFT, SCHEDULED, PUBLISHED = "draft", "scheduled", "published"


def person(user):
    return {"id": user.pk, "name": f"{user.last_name} {user.first_name}".strip()}


# --- お知らせ ---
def notice_status(notice, now=None):
    if notice.published_at is None:
        return DRAFT
    return SCHEDULED if notice.published_at > (now or timezone.now()) else PUBLISHED


class AnnouncementListQuerySerializer(PageQuerySerializer):
    status = serializers.ChoiceField(choices=[DRAFT, SCHEDULED, PUBLISHED], required=False)
    audience = serializers.ChoiceField(choices=Notice.Audience.choices, required=False)
    keyword = serializers.CharField(required=False, max_length=100)


class AnnouncementWriteSerializer(StrictSerializer):
    title = serializers.CharField(max_length=100)
    body = serializers.CharField(max_length=10000)
    audience = serializers.ChoiceField(choices=Notice.Audience.choices)
    published_at = serializers.DateTimeField(allow_null=True)

    def validate(self, attrs):
        if self.partial and not attrs:
            raise serializers.ValidationError({"non_field_errors": ["変更する項目を指定してください。"]})
        return attrs


class AdminAnnouncementSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()

    class Meta:
        model = Notice
        fields = ["id", "title", "audience", "status", "published_at", "created_at", "updated_at"]

    def get_status(self, notice):
        return notice_status(notice)


class AdminAnnouncementDetailSerializer(AdminAnnouncementSerializer):
    class Meta(AdminAnnouncementSerializer.Meta):
        fields = AdminAnnouncementSerializer.Meta.fields + ["body"]


# --- 管理者アカウント ---
class GroupsField(serializers.ListField):
    def __init__(self, **kwargs):
        super().__init__(child=serializers.ChoiceField(choices=STAFF_GROUPS), min_length=1, **kwargs)

    def to_internal_value(self, data):
        return sorted(set(super().to_internal_value(data)), key=STAFF_GROUPS.index)


class AdminCreateSerializer(StrictSerializer):
    email = serializers.EmailField(max_length=254)
    last_name = serializers.CharField(max_length=50)
    first_name = serializers.CharField(max_length=50)
    groups = GroupsField()


class AdminGroupsSerializer(StrictSerializer):
    groups = GroupsField()


class StaffSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    groups = serializers.SerializerMethodField()
    password_set = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "name", "groups", "last_login", "date_joined", "password_set"]

    def get_name(self, user):
        return person(user)["name"]

    def get_groups(self, user):
        names = {g.name for g in user.groups.all()}
        return [name for name in STAFF_GROUPS if name in names]

    def get_password_set(self, user):
        return user.has_usable_password()


# --- 操作ログ ---
class AuditLogQuerySerializer(PageQuerySerializer):
    admin_id = serializers.IntegerField(required=False, min_value=1, max_value=MAX_ID)
    action = serializers.CharField(required=False, max_length=50)
    target_type = serializers.CharField(required=False, max_length=50)
    target_id = serializers.IntegerField(required=False, min_value=1, max_value=MAX_ID)
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)

    def validate(self, attrs):
        if attrs.get("start_date") and attrs.get("end_date") and attrs["start_date"] > attrs["end_date"]:
            raise serializers.ValidationError({"end_date": ["開始日以降の日付を指定してください。"]})
        return attrs


class AuditLogSerializer(serializers.ModelSerializer):
    admin = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = ["id", "admin", "action", "target_type", "target_id", "detail", "created_at"]

    def get_admin(self, log):
        return person(log.admin)


# --- 分析 ---
class AnalyticsQuerySerializer(QuerySerializer):
    year = serializers.IntegerField(required=False, min_value=2000, max_value=2100)
