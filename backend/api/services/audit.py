"""管理者の操作ログ

view から呼ぶ業務ロジック。
管理者によるデータ変更を audit_logs に記録する。
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

# """管理者の操作ログ

# view から呼ぶ業務ロジック。複数のAPI・バッチで同じ処理を使うものをここにまとめる。

# 書くもの:
#   - audit_logs に action・target_type・target_id・detail（理由や変更前後の値）を記録する

# 使う場所:
#   - 管理者APIのデータを変える操作すべて
# """
