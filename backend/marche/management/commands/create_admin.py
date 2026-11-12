"""最初の管理者（「管理者」グループの運営スタッフ）を作る

使い方:
    python manage.py create_admin --email admin@example.com --last-name 山田 --first-name 太郎

- パスワードが使えない状態で作り、パスワード設定のリンクを画面に表示する（メールも送る）。有効期限は1時間
- 2人目からは管理画面（POST /api/v1/admin/admins）で追加する
"""
from django.core.management.base import BaseCommand, CommandError

from api.common.exceptions import Conflict
from api.common.permissions import ADMIN_GROUP
from api.services.staff import create_staff, send_invitation


class Command(BaseCommand):
    help = "最初の管理者アカウントを作り、パスワード設定のリンクを表示する"

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True)
        parser.add_argument("--last-name", required=True)
        parser.add_argument("--first-name", required=True)

    def handle(self, *args, **options):
        try:
            user = create_staff(options["email"], options["last_name"], options["first_name"], [ADMIN_GROUP])
        except Conflict as exc:
            raise CommandError(exc.error_msg) from exc
        if not user.groups.exists():
            raise CommandError("権限グループがありません。先に python manage.py migrate を実行してください。")
        url = send_invitation(user)
        self.stdout.write(f"管理者を作りました: {user.email}\nパスワード設定のリンク（1時間有効）:\n{url}")
