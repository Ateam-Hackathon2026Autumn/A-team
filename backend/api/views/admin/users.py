"""ユーザー管理

認証: 管理者（権限グループ: CS・管理者）。運営スタッフ（is_staff）は対象外（一覧に出さず、:userId で指定しても404）
仕様: api-spec.md「7. 実装で決めたこと」ステップ15（Notion には API の名前だけ）

実装済み:
  - ユーザー一覧: GET /api/v1/admin/users
      ・keyword（メール・氏名・電話の部分一致）・status（active・stopped・withdrawn）・isProducer。登録日時の新しい順
  - ユーザー詳細: GET /api/v1/admin/users/:userId
      ・一覧の項目＋都道府県・producer・counts {orders（支払い済み）, reservations, jobApplications, reviews}・
        activeTransactions（退会のチェックと同じ文言）・reports {made, against}・operationHistory（このユーザーへの操作ログ）
      ・生年月日は返さない
  - 利用停止・再開: PATCH /api/v1/admin/users/:userId/status {action, reason}
      ・stop: reason 必須。is_active=False（Django は停止中の人のセッションを受け付けないので、どの端末もログアウトになる）。
        生産者なら publish_status=suspended。進行中の取引は自動でキャンセルしない（レスポンスの activeTransactions で確認）
      ・resume: is_active=True。生産者の掲載状態は戻さない（掲載の管理の API で再開する）
      ・どちらも本人に理由つきのメール・操作ログ（target_type=user）。状態が合わない → 409 STATUS_CONFLICT、
        退会済み → 409 USER_WITHDRAWN。200 で詳細
  - ユーザー削除: DELETE /api/v1/admin/users/:userId {reason}
      ・退会と同じ匿名化（services/anonymize.py）。進行中の取引があれば 409 ACTIVE_TRANSACTIONS_EXIST（何が残っているかを
        メッセージに書く）。退会済み → 409 USER_WITHDRAWN
      ・匿名化の前に元のメールアドレスへお知らせ。操作ログ（action=delete）。204
"""
from django.db import transaction
from django.db.models import Q
from rest_framework import status as http_status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from marche.models import (AuditLog, JobApplication, Order, Producer, ProductReview, PublishStatus, Report,
                           Reservation, User)

from ...common.exceptions import Conflict
from ...common.pagination import paginate, validate_query
from ...common.permissions import CS_GROUP, AdminGroupPermission
from ...common.serializers import QuerySerializer
from ...serializers.admin.users import (STOPPED, WITHDRAWN, AdminUserDetailSerializer, AdminUserListItemSerializer,
                                        UserDeleteSerializer, UserListQuerySerializer, UserStatusSerializer,
                                        full_name, user_status)
from ...services import mail
from ...services.anonymize import active_transactions, anonymize_user
from ...services.audit import record_audit_log

MAX_ID = 2 ** 63 - 1


def customers():
    """管理の対象のユーザー（運営スタッフを除く）"""
    return User.objects.filter(is_staff=False)


def get_customer(user_id, lock=False):
    users = customers().select_for_update() if lock else customers()
    user = users.filter(pk=user_id).first() if user_id <= MAX_ID else None
    if user is None:
        raise NotFound()
    return user


def load_detail(user_id):
    user = customers().select_related("producer", "prefecture").get(pk=user_id)
    producer = getattr(user, "producer", None)
    user.counts = {
        "orders": Order.objects.filter(user=user, payment_status=Order.PaymentStatus.PAID).count(),
        "reservations": Reservation.objects.filter(user=user).count(),
        "job_applications": JobApplication.objects.filter(user=user).count(),
        "reviews": ProductReview.objects.filter(user=user).count(),
    }
    user.active_transactions = active_transactions(user)
    against = Q(target_type=Report.TargetType.USER, target_id=user.pk)
    if producer is not None:
        against |= Q(target_type=Report.TargetType.PRODUCER, target_id=producer.pk)
    user.reports = {"made": Report.objects.filter(reporter=user).count(),
                    "against": Report.objects.filter(against).count()}
    user.operation_history = list(AuditLog.objects.filter(target_type="user", target_id=user.pk)
                                  .select_related("admin").order_by("-created_at", "-id"))
    return user


class AdminUserListView(APIView):
    """GET /api/v1/admin/users"""

    permission_classes = [AdminGroupPermission]
    admin_groups = [CS_GROUP]

    def get(self, request):
        query = validate_query(UserListQuerySerializer, request)
        users = customers()
        keyword = (query.get("keyword") or "").strip()
        if keyword:
            users = users.filter(Q(email__icontains=keyword) | Q(last_name__icontains=keyword)
                                 | Q(first_name__icontains=keyword) | Q(phone__icontains=keyword))
        state = query.get("status")
        if state == WITHDRAWN:
            users = users.filter(deleted_at__isnull=False)
        elif state == STOPPED:
            users = users.filter(deleted_at__isnull=True, is_active=False)
        elif state:
            users = users.filter(deleted_at__isnull=True, is_active=True)
        if query.get("is_producer") is not None:
            users = users.filter(producer__isnull=not query["is_producer"])
        rows = users.select_related("producer").order_by("-date_joined", "-id")
        return Response(paginate(rows, query, AdminUserListItemSerializer, count_queryset=users))


class AdminUserDetailView(APIView):
    """GET・DELETE /api/v1/admin/users/:userId"""

    permission_classes = [AdminGroupPermission]
    admin_groups = [CS_GROUP]

    def get(self, request, user_id):
        validate_query(QuerySerializer, request)
        return Response(AdminUserDetailSerializer(load_detail(get_customer(user_id).pk)).data)

    def delete(self, request, user_id):
        serializer = UserDeleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data["reason"]
        with transaction.atomic():
            user = get_customer(user_id, lock=True)
            if user.deleted_at is not None:
                raise Conflict("USER_WITHDRAWN", "このユーザーはすでに退会済みです。")
            remaining = active_transactions(user)
            if remaining:
                raise Conflict("ACTIVE_TRANSACTIONS_EXIST",
                               "次の取引が終わるまで削除できません：" + "、".join(remaining))
            email, name = user.email, full_name(user) or "お客様"
            anonymize_user(user)
            record_audit_log(admin=request.user, action="delete", target_type="user", target_id=user.pk,
                             detail={"reason": reason})
            transaction.on_commit(lambda: mail.send_admin_notice(
                email, name, "アカウントを削除しました",
                "運営の判断により、つながるマルシェのアカウントを削除しました。\n"
                "ご登録の情報は削除し、ログインもできなくなりました。"))
        return Response(status=http_status.HTTP_204_NO_CONTENT)


class AdminUserStatusView(APIView):
    """PATCH /api/v1/admin/users/:userId/status"""

    permission_classes = [AdminGroupPermission]
    admin_groups = [CS_GROUP]

    def patch(self, request, user_id):
        serializer = UserStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        action, reason = serializer.validated_data["action"], serializer.validated_data["reason"]
        with transaction.atomic():
            user = get_customer(user_id, lock=True)
            before = user_status(user)
            if before == WITHDRAWN:
                raise Conflict("USER_WITHDRAWN", "このユーザーは退会済みです。")
            if (action == "stop") != (before != STOPPED):
                raise Conflict("STATUS_CONFLICT", "すでに利用停止中です。" if action == "stop" else "利用停止中ではありません。")

            detail = {"reason": reason, "before": before}
            user.is_active = action != "stop"
            user.save(update_fields=["is_active", "updated_at"])
            detail["after"] = user_status(user)
            if action == "stop":
                producer = Producer.objects.select_for_update().filter(user=user).first()
                if producer is not None and producer.publish_status != PublishStatus.SUSPENDED:
                    detail["producer_publish_status_before"] = producer.publish_status
                    producer.publish_status = PublishStatus.SUSPENDED
                    producer.save(update_fields=["publish_status", "updated_at"])
            record_audit_log(admin=request.user, action=action, target_type="user", target_id=user.pk,
                             detail=detail)
            self.send_notice(user, action, reason)
        return Response(AdminUserDetailSerializer(load_detail(user.pk)).data)

    @staticmethod
    def send_notice(user, action, reason):
        email, name = user.email, full_name(user) or "お客様"
        if action == "stop":
            subject = "アカウントの利用を停止しました"
            message = ("運営の判断により、つながるマルシェのアカウントの利用を停止しました。\n"
                       f"停止中はログインできません。\n\n理由：\n{reason}")
        else:
            subject = "アカウントの利用停止を解除しました"
            message = "つながるマルシェのアカウントの利用停止を解除しました。またログインしてご利用いただけます。"
            if reason:
                message += f"\n\n運営からのコメント：\n{reason}"
        transaction.on_commit(lambda: mail.send_admin_notice(email, name, subject, message))
