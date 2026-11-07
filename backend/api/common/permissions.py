"""権限クラス

生産者APIの共通チェック（api-spec「生産者APIの共通チェック」）:
  - ログインしていなければ 401
  - 自分の producers がない、または approval_status が approved でなければ 403（FORBIDDEN）
  - 生産者が掲載停止中（producers.publish_status=suspended）のときにできない操作は 409（PRODUCER_SUSPENDED）
      できる: 閲覧、プロフィール更新、配送設定、発送・キャンセル承認拒否、採用・不採用、予約枠の中止
      できない: 商品・体験・求人・ストーリー・予約枠の登録・更新・削除、在庫更新、レビュー返信
    → できない操作の view の中で ensure_producer_not_suspended(producer) を呼ぶ

使い方:
    class XxxView(APIView):
        permission_classes = [IsApprovedProducer]

        def post(self, request):
            producer = request.user.producer
            ensure_producer_not_suspended(producer)

管理者APIの共通チェック（api-spec「管理者APIの共通チェック」）:
  - ログインしていなければ 401
  - is_staff=True で、許可された権限グループのどれかに入っていなければ 403（FORBIDDEN）
  - 「管理者」グループはすべての管理者APIを使える
  - 権限グループ: 審査担当（生産者審査・掲載停止）／CS（ユーザー・問い合わせ・通報・注文・返金）／管理者（すべて）

使い方（view にグループを書く）:
    class XxxView(APIView):
        permission_classes = [AdminGroupPermission]
        admin_groups = [REVIEWER_GROUP]

    よく使う組み合わせは専用のクラスがある: IsAdminCSOrAdmin（CS・管理者）
"""
from rest_framework.permissions import BasePermission

from marche.models import Producer, PublishStatus

from .exceptions import Conflict


class IsApprovedProducer(BasePermission):
    """承認済みの生産者だけ通す。未ログインは DRF が 401 にする"""

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        producer = getattr(user, "producer", None)  # 生産者でなければ None
        return producer is not None and producer.approval_status == Producer.ApprovalStatus.APPROVED


def ensure_producer_not_suspended(producer):
    """生産者が掲載停止中なら 409 にする（登録・更新・削除の前に呼ぶ）"""
    if producer.publish_status == PublishStatus.SUSPENDED:
        raise Conflict("PRODUCER_SUSPENDED",
                        "掲載停止中のため、この操作はできません。運営にお問い合わせください。")


# 権限グループの名前（auth_group.name）
ADMIN_GROUP = "管理者"
CS_GROUP = "CS"
REVIEWER_GROUP = "審査担当"


class AdminGroupPermission(BasePermission):
    """運営スタッフ（is_staff）で、許可されたグループのどれかに入っている人だけ通す。未ログインは DRF が 401 にする

    許可するグループは、クラスの allowed_groups か、view の admin_groups に書く。「管理者」は常に許可する。
    """

    allowed_groups = None

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated and user.is_staff):
            return False
        groups = set(self.allowed_groups or getattr(view, "admin_groups", ())) | {ADMIN_GROUP}
        return user.groups.filter(name__in=groups).exists()


class IsAdminCSOrAdmin(AdminGroupPermission):
    """CS・管理者グループ（注文・返金、ユーザー管理、問い合わせ・通報）"""

    allowed_groups = [CS_GROUP]
