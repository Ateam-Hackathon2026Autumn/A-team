"""管理者ログイン のシリアライザー

使う view: api/views/admin/auth.py
- ログインの本文は会員側と同じ（SigninSerializer を使う）
- 管理者の user: {id, email, lastName, firstName, groups}（groups は権限グループ名の配列。審査担当・CS・管理者）
"""
from rest_framework import serializers

from marche.models import User


class AdminUserSerializer(serializers.ModelSerializer):
    groups = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "last_name", "first_name", "groups"]

    def get_groups(self, user):
        return sorted(group.name for group in user.groups.all())
