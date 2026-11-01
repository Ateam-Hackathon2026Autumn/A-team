"""認証（ログイン・ログアウト・メール認証）のシリアライザー
入力データを検証したり、ログインしたユーザーの情報をJSONに変換したりするシリアライザーを定義

使う view: api/views/public/auth.py、api/views/public/users.py（新規登録のレスポンス）
JSON のキーはレンダラー・パーサーがキャメルケースに変換する（last_name ⇔ lastName）。
"""
from rest_framework import serializers

from marche.models import Producer, PublishStatus

from ...common.serializers import StrictSerializer


class AuthUserSerializer(serializers.Serializer):
    """Notion「認証・ユーザーAPI 共通定義」の User。ログイン・新規登録・ログインチェックで返す"""

    id = serializers.IntegerField()
    email = serializers.EmailField()
    last_name = serializers.CharField()
    first_name = serializers.CharField()
    is_producer = serializers.SerializerMethodField()
    producer_application_status = serializers.SerializerMethodField()
    producer_account_status = serializers.SerializerMethodField()
    email_verified = serializers.BooleanField()

    @staticmethod
    def _producer(user):
        return getattr(user, "producer", None)

    def get_is_producer(self, user):
        # 承認済みなら true。掲載停止中でもダッシュボードの閲覧・発送はできるので true のまま（停止中かは producerAccountStatus で見る）
        producer = self._producer(user)
        return producer is not None and producer.approval_status == Producer.ApprovalStatus.APPROVED

    def get_producer_application_status(self, user):
        # not_applied / pending / approved / rejected / returned（差し戻し）
        producer = self._producer(user)
        return producer.approval_status if producer else "not_applied"

    def get_producer_account_status(self, user):
        # 生産者でなければ null。運営に掲載停止されていれば suspended、それ以外は active
        producer = self._producer(user)
        if producer is None:
            return None
        return "suspended" if producer.publish_status == PublishStatus.SUSPENDED else "active"


class SigninSerializer(StrictSerializer):
    """POST /api/v1/auth/signin"""

    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(max_length=128, trim_whitespace=False)


class EmailVerificationConfirmSerializer(StrictSerializer):
    """POST /api/v1/auth/email-verification/confirm"""

    token = serializers.CharField(max_length=512)
