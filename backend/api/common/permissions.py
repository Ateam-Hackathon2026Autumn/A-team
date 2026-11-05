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

管理者の権限:
  - is_staff=True かつ CS または 管理者グループに所属していること
  - 管理者向け注文APIでは IsAdminCSOrAdmin を使用する
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


class IsAdminCSOrAdmin(BasePermission):
    """CS または管理者グループに所属する運営スタッフだけ通す。

    条件:
      - ログイン済み
      - is_staff=True
      - CS または 管理者グループに所属
    """

    allowed_groups = ["CS", "管理者"]

    def has_permission(self, request, view):
        user = request.user

        if not (user and user.is_authenticated):
            return False

        if not user.is_staff:
            return False

        return user.groups.filter(
            name__in=self.allowed_groups
        ).exists()
