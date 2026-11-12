"""管理者の管理（運営スタッフのアカウントと権限グループ）

認証: 管理者（権限グループ: 管理者）
仕様: api-spec.md「7. 実装で決めたこと」ステップ16（Notion には API の名前だけ）

実装済み:
  - 管理者一覧: GET /api/v1/admin/admins
      ・運営スタッフ（is_staff）を全員。人数が少ないのでページングなし。{items: [{id, email, name, groups, lastLogin,
        dateJoined, passwordSet}]}。登録の古い順
  - 管理者追加: POST /api/v1/admin/admins {email, lastName, firstName, groups}
      ・is_staff のアカウントをパスワードが使えない状態で作り、パスワード設定のメールを送る（services/staff.py）
      ・使われているメール（お客さんのアカウントを含む）は 409 EMAIL_IN_USE。201
  - 管理者の権限変更: PATCH /api/v1/admin/admins/:adminId {groups}
      ・置き換え（1つ以上）。自分自身は 409 CANNOT_CHANGE_SELF、「管理者」の最後の1人を外すのは 409 LAST_ADMIN
  - 管理者削除: DELETE /api/v1/admin/admins/:adminId
      ・is_active=False・is_staff=False・グループを外す（行は残す。Django は停止中の人のセッションを受け付けないので
        全端末ログアウト）。自分自身は 409 CANNOT_CHANGE_SELF、最後の管理者は 409 LAST_ADMIN。204
  - 追加・変更・削除は操作ログ（target_type=admin）
"""
from django.contrib.auth.models import Group
from django.db import transaction
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from marche.models import User

from ...common.exceptions import Conflict
from ...common.pagination import validate_query
from ...common.permissions import ADMIN_GROUP, AdminGroupPermission
from ...common.serializers import QuerySerializer
from ...serializers.admin.settings import MAX_ID, AdminCreateSerializer, AdminGroupsSerializer, StaffSerializer
from ...services.audit import record_audit_log
from ...services.staff import admin_count, create_staff, send_invitation


def staff_members():
    return User.objects.filter(is_staff=True).prefetch_related("groups")


def get_staff(request, admin_id):
    """変更の対象のスタッフを行ロックして返す（自分自身は 409）"""
    staff = User.objects.select_for_update().filter(pk=admin_id, is_staff=True).first() if admin_id <= MAX_ID else None
    if staff is None:
        raise NotFound()
    if staff.pk == request.user.pk:
        raise Conflict("CANNOT_CHANGE_SELF", "ご自身の権限は変更・削除できません。ほかの管理者に依頼してください。")
    return staff


def ensure_admin_remains(staff, keeps_admin):
    """この人が「管理者」から外れると、管理者が0人になるなら 409"""
    is_admin = staff.groups.filter(name=ADMIN_GROUP).exists()
    if is_admin and not keeps_admin and admin_count(exclude=staff) == 0:
        raise Conflict("LAST_ADMIN", "「管理者」グループの最後の1人は外せません。先にほかの人を管理者にしてください。")


def lock_admins():
    """最後の1人の確認が同時に通らないよう、管理者グループのスタッフの行をロックする"""
    list(User.objects.select_for_update().filter(is_staff=True, groups__name=ADMIN_GROUP).values_list("pk", flat=True))


class AdminStaffListView(APIView):
    """GET・POST /api/v1/admin/admins"""

    permission_classes = [AdminGroupPermission]

    def get(self, request):
        validate_query(QuerySerializer, request)
        return Response({"items": StaffSerializer(staff_members().order_by("date_joined", "id"), many=True).data})

    def post(self, request):
        serializer = AdminCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        with transaction.atomic():
            staff = create_staff(data["email"], data["last_name"], data["first_name"], data["groups"])
            record_audit_log(admin=request.user, action="create", target_type="admin", target_id=staff.pk,
                             detail={"email": staff.email, "groups": data["groups"]})
            transaction.on_commit(lambda: send_invitation(staff))
        return Response(StaffSerializer(staff_members().get(pk=staff.pk)).data, status=status.HTTP_201_CREATED)


class AdminStaffDetailView(APIView):
    """PATCH・DELETE /api/v1/admin/admins/:adminId"""

    permission_classes = [AdminGroupPermission]

    def patch(self, request, admin_id):
        serializer = AdminGroupsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        groups = serializer.validated_data["groups"]
        with transaction.atomic():
            lock_admins()
            staff = get_staff(request, admin_id)
            ensure_admin_remains(staff, keeps_admin=ADMIN_GROUP in groups)
            before = sorted(staff.groups.values_list("name", flat=True))
            staff.groups.set(Group.objects.filter(name__in=groups))
            record_audit_log(admin=request.user, action="update", target_type="admin", target_id=staff.pk,
                             detail={"before": before, "after": groups})
        return Response(StaffSerializer(staff_members().get(pk=staff.pk)).data)

    def delete(self, request, admin_id):
        with transaction.atomic():
            lock_admins()
            staff = get_staff(request, admin_id)
            ensure_admin_remains(staff, keeps_admin=False)
            before = sorted(staff.groups.values_list("name", flat=True))
            staff.is_active = False
            staff.is_staff = False
            staff.save(update_fields=["is_active", "is_staff", "updated_at"])
            staff.groups.clear()
            record_audit_log(admin=request.user, action="delete", target_type="admin", target_id=staff.pk,
                             detail={"email": staff.email, "groups": before})
        return Response(status=status.HTTP_204_NO_CONTENT)
