"""管理者の操作ログ

管理者APIのデータを変える操作はすべて、record_audit_log() で audit_logs に記録する（api-spec「管理者APIの共通チェック」）。
- action: approve / suspend / resume / cancel / refund など
- target_type・target_id: 対象の種類（order・producer など）と ID
- detail: 理由や変更前後の値（JSON）

使う場所: 管理者の注文キャンセル・返金（実装済み）、審査・掲載停止・ユーザー管理などの管理者API
"""

from marche.models import AuditLog


def record_audit_log(
    admin,
    action,
    target_type,
    target_id,
    detail=None,
):
    """管理者の操作ログを記録する。

    Args:
        admin: 操作した管理者ユーザー
        action: 操作内容
        target_type: 操作対象の種類
        target_id: 操作対象のID
        detail: 理由や変更前後の値など
    """

    return AuditLog.objects.create(
        admin=admin,
        action=action,
        target_type=target_type,
        target_id=target_id,
        detail=detail,
    )
