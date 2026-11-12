"""問い合わせ対応 のシリアライザー

使う view: api/views/admin/inquiries.py

  - 一覧のクエリ: InquiryListQuerySerializer {status, priority, category, assigneeId, keyword, page, pageSize}
      ・status はカンマ区切りで複数（初期値 open,in_progress）。assigneeId は数字か me（自分の担当）
  - 一覧の1件: AdminInquiryListItemSerializer {id, category, subject, email, status, priority, assignee, userId, orderId,
      createdAt, updatedAt}
  - 詳細: AdminInquiryDetailSerializer（一覧の項目＋body・user・order・notes）
  - 更新の本文: InquiryUpdateSerializer {status, priority, assigneeId, note}（1つ以上）

入力エラーは 400（項目ごとのメッセージ）。カラム名は claude/er-diagram.md に合わせる
"""
from rest_framework import serializers

from marche.models import Inquiry, InquiryNote

from ...common.pagination import PageQuerySerializer
from ...common.serializers import StrictSerializer

MAX_ID = 2 ** 63 - 1
DEFAULT_STATUSES = [Inquiry.Status.OPEN, Inquiry.Status.IN_PROGRESS]


def person(user):
    if user is None:
        return None
    return {"id": user.pk, "name": f"{user.last_name} {user.first_name}".strip()}


class InquiryListQuerySerializer(PageQuerySerializer):
    status = serializers.CharField(required=False, max_length=100)
    priority = serializers.ChoiceField(choices=Inquiry.Priority.choices, required=False)
    category = serializers.ChoiceField(choices=Inquiry.Category.choices, required=False)
    assignee_id = serializers.CharField(required=False, max_length=20)
    keyword = serializers.CharField(required=False, max_length=100)

    def validate_status(self, value):
        statuses = [v.strip() for v in value.split(",") if v.strip()]
        allowed = set(Inquiry.Status.values)
        if not statuses or any(v not in allowed for v in statuses):
            raise serializers.ValidationError("open・in_progress・closed をカンマ区切りで指定してください。")
        return statuses

    def validate_assignee_id(self, value):
        if value == "me":
            return value
        if not value.isdigit() or not 1 <= int(value) <= MAX_ID:
            raise serializers.ValidationError("担当者のIDか me を指定してください。")
        return int(value)


class InquiryUpdateSerializer(StrictSerializer):
    status = serializers.ChoiceField(choices=Inquiry.Status.choices, required=False)
    priority = serializers.ChoiceField(choices=Inquiry.Priority.choices, required=False)
    assignee_id = serializers.IntegerField(min_value=1, max_value=MAX_ID, required=False, allow_null=True)
    note = serializers.CharField(max_length=2000, required=False)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError({"non_field_errors": ["変更する項目を指定してください。"]})
        return attrs


class AdminInquiryListItemSerializer(serializers.ModelSerializer):
    assignee = serializers.SerializerMethodField()

    class Meta:
        model = Inquiry
        fields = ["id", "category", "subject", "email", "status", "priority", "assignee", "user_id", "order_id",
                  "created_at", "updated_at"]

    def get_assignee(self, inquiry):
        return person(inquiry.assignee)


class InquiryNoteSerializer(serializers.ModelSerializer):
    author = serializers.SerializerMethodField()

    class Meta:
        model = InquiryNote
        fields = ["id", "author", "body", "created_at"]

    def get_author(self, note):
        return person(note.author)


class AdminInquiryDetailSerializer(AdminInquiryListItemSerializer):
    user = serializers.SerializerMethodField()
    order = serializers.SerializerMethodField()
    notes = InquiryNoteSerializer(source="inquiry_notes", many=True)

    class Meta(AdminInquiryListItemSerializer.Meta):
        fields = AdminInquiryListItemSerializer.Meta.fields + ["body", "user", "order", "notes"]

    def get_user(self, inquiry):
        return person(inquiry.user)

    def get_order(self, inquiry):
        order = inquiry.order
        return {"id": order.pk, "order_no": order.order_no} if order else None
