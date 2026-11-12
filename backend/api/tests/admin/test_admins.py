"""管理者の管理 のテスト

テスト対象: api/views/admin/admins.py・services/staff.py・管理コマンド create_admin
  - 管理者一覧・追加（パスワード設定のメール）・権限の変更・削除。自分自身・最後の管理者は 409
"""
import re
from io import StringIO

from django.core import mail
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client

from marche.models import AuditLog, User

from ...common.exceptions import Conflict
from ...views.admin.admins import ensure_admin_remains
from ..utils import ApiTestCase, make_user
from .test_producer_applications import make_staff

BASE = "/api/v1/admin/admins"


class AdminStaffTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.me = make_staff("admin@example.com", "管理者")
        self.signin(self.me.email)

    def test_create_and_set_password(self):
        with self.captureOnCommitCallbacks(execute=True):
            res = self.post_json(BASE, {"email": "New@Example.com", "lastName": "鈴木", "firstName": "一郎",
                                        "groups": ["審査担当", "CS", "CS"]})
        self.assertEqual(res.status_code, 201, res.json())
        self.assertEqual((res.json()["email"], res.json()["groups"], res.json()["passwordSet"]),
                         ("new@example.com", ["CS", "審査担当"], False))
        staff = User.objects.get(email="new@example.com")
        self.assertTrue(staff.is_staff)
        self.assertEqual(mail.outbox[0].to, ["new@example.com"])
        url = re.search(r"http\S+", mail.outbox[0].body).group(0)
        uid, token = re.search(r"uid=([^&]+)&token=(\S+)", url).groups()
        browser = Client()
        browser.get("/api/v1/auth/csrf")
        res = browser.post("/api/v1/auth/password-reset/confirm",
                           {"uid": uid, "token": token, "newPassword": "StaffPass123!"}, content_type="application/json",
                           HTTP_X_CSRFTOKEN=browser.cookies["csrftoken"].value)
        self.assertEqual(res.status_code, 200, res.json())
        self.assertTrue(User.objects.get(pk=staff.pk).check_password("StaffPass123!"))
        self.assertEqual(AuditLog.objects.get().action, "create")
        items = self.client.get(BASE).json()["items"]
        self.assertEqual([(i["email"], i["passwordSet"]) for i in items],
                         [("admin@example.com", True), ("new@example.com", True)])

    def test_create_errors(self):
        make_user(email="buyer@example.com")
        res = self.post_json(BASE, {"email": "buyer@example.com", "lastName": "a", "firstName": "b", "groups": ["CS"]})
        self.assertEqual((res.status_code, res.json()["errorCode"]), (409, "EMAIL_IN_USE"))
        for groups in [[], ["スーパー管理者"]]:
            res = self.post_json(BASE, {"email": "x@example.com", "lastName": "a", "firstName": "b", "groups": groups})
            self.assertEqual(res.status_code, 400)
            self.assertTrue(all(key.startswith("groups") for key in res.json()["details"]), res.json())

    def test_update_groups(self):
        other = make_staff("cs@example.com", "CS")
        res = self.patch_json(f"{BASE}/{other.id}", {"groups": ["管理者"]})
        self.assertEqual((res.status_code, res.json()["groups"]), (200, ["管理者"]))
        res = self.patch_json(f"{BASE}/{self.me.id}", {"groups": ["CS"]})
        self.assertEqual((res.status_code, res.json()["errorCode"]), (409, "CANNOT_CHANGE_SELF"))
        self.assertEqual(self.patch_json(f"{BASE}/{other.id}", {"groups": ["CS"]}).status_code, 200)
        self.assertEqual(self.patch_json(f"{BASE}/{make_user(email='c@example.com').id}", {"groups": ["CS"]})
                         .status_code, 404)

    def test_delete(self):
        other = make_staff("cs@example.com", "CS")
        device = Client()
        device.force_login(other)
        self.assertEqual(self.delete_json(f"{BASE}/{other.id}").status_code, 204)
        other = User.objects.get(pk=other.pk)
        self.assertEqual((other.is_active, other.is_staff, other.groups.count()), (False, False, 0))
        self.assertEqual(device.get("/api/v1/admin/summary").status_code, 401)   # ほかの端末もログアウト
        self.assertEqual([i["id"] for i in self.client.get(BASE).json()["items"]], [self.me.id])
        res = self.delete_json(f"{BASE}/{self.me.id}")
        self.assertEqual((res.status_code, res.json()["errorCode"]), (409, "CANNOT_CHANGE_SELF"))

    def test_permission(self):
        self.post_json("/api/v1/admin/auth/signout")
        self.signin(make_staff("cs@example.com", "CS").email)
        self.assertEqual(self.client.get(BASE).status_code, 403)


class LastAdminTests(ApiTestCase):
    """「管理者」グループの最後の1人は外せない

    API では操作する人自身が管理者なので、ほかの人を外しても管理者は0人にならない（自分自身は CANNOT_CHANGE_SELF）。
    データの直接の変更などで起きないよう、確認の関数を直接確かめる
    """

    def test_ensure_admin_remains(self):
        only_admin = make_staff("admin@example.com", "管理者")
        cs = make_staff("cs@example.com", "CS")
        with self.assertRaises(Conflict) as ctx:
            ensure_admin_remains(only_admin, keeps_admin=False)
        self.assertEqual(ctx.exception.error_code, "LAST_ADMIN")
        ensure_admin_remains(only_admin, keeps_admin=True)   # 管理者のままなら通る
        ensure_admin_remains(cs, keeps_admin=False)          # 管理者でない人は関係ない
        make_staff("admin2@example.com", "管理者")
        ensure_admin_remains(only_admin, keeps_admin=False)  # ほかに管理者がいれば通る


class CreateAdminCommandTests(ApiTestCase):
    def test_command(self):
        out = StringIO()
        call_command("create_admin", "--email", "first@example.com", "--last-name", "山田", "--first-name", "太郎",
                     stdout=out)
        staff = User.objects.get(email="first@example.com")
        self.assertEqual((staff.is_staff, list(staff.groups.values_list("name", flat=True)), staff.has_usable_password()),
                         (True, ["管理者"], False))
        self.assertIn("/password-reset/confirm?uid=", out.getvalue())
        with self.assertRaises(CommandError):
            call_command("create_admin", "--email", "first@example.com", "--last-name", "a", "--first-name", "b",
                         stdout=StringIO())
