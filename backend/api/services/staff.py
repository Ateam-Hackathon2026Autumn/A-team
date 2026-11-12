"""運営スタッフ（管理者アカウント）の作成・権限

view と管理コマンドから呼ぶ業務ロジック。

実装済み:
  - STAFF_GROUPS: 権限グループの名前（管理者・CS・審査担当。マイグレーション 0012 で作る）
  - create_staff(email, last_name, first_name, group_names): is_staff のアカウントを、パスワードが使えない状態で作る。
      メール確認済みにする（パスワード設定のリンクをメールで受け取るため）。同じメールがあれば 409 EMAIL_IN_USE
  - send_invitation(user): パスワード設定のリンク（パスワード再設定と同じ仕組み・有効期限1時間）をメールで送り、URL を返す
      期限が切れたら、本人がパスワード再設定の画面から申請する
  - admin_count(exclude=None): 「管理者」グループの利用中のスタッフの数（最後の1人を外さないための確認）

使う場所: api/views/admin/admins.py、marche/management/commands/create_admin.py
"""
from django.contrib.auth.models import Group
from django.utils import timezone

from marche.models import User

from ..common.exceptions import Conflict
from ..common.permissions import ADMIN_GROUP, CS_GROUP, REVIEWER_GROUP
from . import mail, password_reset

STAFF_GROUPS = [ADMIN_GROUP, CS_GROUP, REVIEWER_GROUP]


def create_staff(email, last_name, first_name, group_names):
    email = User.objects.normalize_email(email)
    if User.objects.filter(email=email).exists():
        raise Conflict("EMAIL_IN_USE", "このメールアドレスはすでに使われています。")
    user = User.objects.create_user(email=email, password=None, last_name=last_name, first_name=first_name,
                                    is_staff=True, email_verified_at=timezone.now())
    user.groups.set(Group.objects.filter(name__in=group_names))
    return user


def send_invitation(user):
    url = password_reset.make_url(user)
    name = f"{user.last_name} {user.first_name}".strip()
    mail.send(user.email, "管理画面のアカウントを作成しました",
              f"{name} 様\n\nつながるマルシェの管理画面のアカウントを作成しました。\n"
              "下のリンクを開いて、パスワードを設定してください。\n\n"
              f"{url}\n\n"
              "このリンクの有効期限は1時間です。期限が切れたときは、ログイン画面の「パスワードを忘れた方」から"
              "このメールアドレスで申請してください。\n")
    return url


def admin_count(exclude=None):
    staff = User.objects.filter(is_staff=True, is_active=True, groups__name=ADMIN_GROUP)
    if exclude is not None:
        staff = staff.exclude(pk=exclude.pk)
    return staff.count()
