"""ユーザー管理 のシリアライザー

使う view: api/views/admin/users.py

  - 一覧のクエリ: UserListQuerySerializer {keyword, status, isProducer, page, pageSize}
  - 一覧の1件: AdminUserListItemSerializer {id, email, name, phone, status, isProducer, producerId, emailVerified,
      dateJoined, lastLogin}。status は active（利用中）・stopped（停止中）・withdrawn（退会済み）
  - 詳細: AdminUserDetailSerializer（一覧の項目＋prefectureName・producer・counts・activeTransactions・reports・
      operationHistory。counts などは view が付ける）
  - 利用停止・再開の本文: UserStatusSerializer {action: stop|resume, reason}（stop は reason 必須）
  - 削除の本文: UserDeleteSerializer {reason}（必須）

入力エラーは 400（項目ごとのメッセージ）。カラム名は claude/er-diagram.md に合わせる
"""
from rest_framework import serializers

from marche.models import User

from ...common.pagination import PageQuerySerializer
from ...common.serializers import QueryBooleanField, StrictSerializer
from .orders import AdminAuditLogSerializer

ACTIVE, STOPPED, WITHDRAWN = "active", "stopped", "withdrawn"


def user_status(user):
    if user.deleted_at is not None:
        return WITHDRAWN
    return ACTIVE if user.is_active else STOPPED


def full_name(user):
    return f"{user.last_name} {user.first_name}".strip()


class UserListQuerySerializer(PageQuerySerializer):
    keyword = serializers.CharField(required=False, max_length=100)
    status = serializers.ChoiceField(choices=[ACTIVE, STOPPED, WITHDRAWN], required=False)
    is_producer = QueryBooleanField(required=False, allow_null=True, default=None)


def _reason_field(required):
    return serializers.CharField(max_length=1000, required=required, allow_blank=not required,
                                 allow_null=not required)


class UserStatusSerializer(StrictSerializer):
    action = serializers.ChoiceField(choices=["stop", "resume"])
    reason = _reason_field(required=False)

    def validate(self, attrs):
        attrs["reason"] = attrs.get("reason") or None
        if attrs["action"] == "stop" and attrs["reason"] is None:
            raise serializers.ValidationError({"reason": ["利用停止の理由を入力してください。"]})
        return attrs


class UserDeleteSerializer(StrictSerializer):
    reason = _reason_field(required=True)


class AdminUserListItemSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    is_producer = serializers.SerializerMethodField()
    producer_id = serializers.SerializerMethodField()
    email_verified = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "name", "phone", "status", "is_producer", "producer_id", "email_verified",
                  "date_joined", "last_login"]

    def get_name(self, user):
        return full_name(user)

    def get_status(self, user):
        return user_status(user)

    @staticmethod
    def _producer(user):
        return getattr(user, "producer", None)

    def get_is_producer(self, user):
        return self._producer(user) is not None

    def get_producer_id(self, user):
        producer = self._producer(user)
        return producer.id if producer else None

    def get_email_verified(self, user):
        return user.email_verified_at is not None


class AdminUserDetailSerializer(AdminUserListItemSerializer):
    prefecture_name = serializers.CharField(source="prefecture.name", allow_null=True, default=None)
    producer = serializers.SerializerMethodField()
    counts = serializers.DictField()
    active_transactions = serializers.ListField(child=serializers.CharField())
    reports = serializers.DictField()
    operation_history = AdminAuditLogSerializer(many=True)

    class Meta(AdminUserListItemSerializer.Meta):
        fields = AdminUserListItemSerializer.Meta.fields + [
            "prefecture_name", "producer", "counts", "active_transactions", "reports", "operation_history"]

    def get_producer(self, user):
        producer = self._producer(user)
        if producer is None:
            return None
        return {"id": producer.id, "business_name": producer.business_name,
                "publish_status": producer.publish_status, "approval_status": producer.approval_status}
