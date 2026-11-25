"""Django 標準の管理画面（/api/django-admin/。marche/admin.py）のテスト"""
import importlib

from django.conf import settings
from django.contrib import admin
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import clear_url_caches

from marche.models import Product, User

URL = "/api/django-admin/"


def reload_urls():
    import config.urls
    clear_url_caches()
    importlib.reload(config.urls)


class DjangoAdminPagesTests(TestCase):
    """開発用データを入れて、登録したすべてのテーブルの画面が開けることを確かめる"""

    @classmethod
    def setUpTestData(cls):
        with override_settings(DEBUG=True):
            call_command("seed_dev", stdout=open("/dev/null", "w"))
        cls.superuser = User.objects.create_superuser("root@example.com", "Root#Pass2026", last_name="運営",
                                                      first_name="太郎")

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_index_lists_tables(self):
        res = self.client.get(URL)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "つながるマルシェ 管理画面")
        self.assertContains(res, "商品")

    def test_every_registered_table_opens(self):
        for model, model_admin in admin.site._registry.items():
            if model._meta.app_label != "marche":
                continue
            name = model._meta.model_name
            base = f"{URL}marche/{name}/"
            with self.subTest(model=name):
                self.assertEqual(self.client.get(base).status_code, 200)
                if model_admin.search_fields:
                    self.assertEqual(self.client.get(base, {"q": "a"}).status_code, 200)
                obj = model.objects.order_by("pk").first()
                if obj is not None:
                    self.assertEqual(self.client.get(f"{base}{obj.pk}/change/").status_code, 200)
                    # 削除はどのテーブルもできない
                    self.assertEqual(self.client.get(f"{base}{obj.pk}/delete/").status_code, 403)

    def test_orders_are_view_only(self):
        res = self.client.get(f"{URL}marche/order/add/")
        self.assertEqual(res.status_code, 403)

    def test_sale_price_is_read_only_and_follows_discount(self):
        product = Product.objects.filter(discount_rate__isnull=True).order_by("pk").first()
        res = self.client.get(f"{URL}marche/product/{product.pk}/change/")
        self.assertNotContains(res, 'name="sale_price"')  # 入力欄はない（表示だけ）
        self.assertContains(res, f'<div class="readonly">{product.sale_price}</div>', html=True)

    def test_staff_without_superuser_and_members_cannot_use(self):
        self.client.logout()
        self.assertEqual(self.client.get(URL).status_code, 302)  # ログイン画面へ
        member = User.objects.get(email="buyer1@example.com")
        self.client.force_login(member)
        self.assertEqual(self.client.get(f"{URL}marche/product/").status_code, 302)


class DjangoAdminSwitchTests(TestCase):
    def tearDown(self):
        reload_urls()

    @override_settings(DJANGO_ADMIN_ENABLED=False)
    def test_disabled_admin_is_404(self):
        reload_urls()
        self.assertEqual(self.client.get(URL).status_code, 404)
        self.assertEqual(self.client.get("/api/health/").status_code, 200)

    @override_settings(DJANGO_ADMIN_ENABLED=True)
    def test_enabled_admin_shows_login(self):
        reload_urls()
        self.assertEqual(self.client.get(URL).status_code, 302)
        self.assertEqual(self.client.get(f"{URL}login/").status_code, 200)

    def test_static_files_are_under_api(self):
        """CloudFront は /api/* だけをバックエンドに流すので、CSS も /api/ の下から返す"""
        self.assertEqual(settings.STATIC_URL, "/api/static/")
        self.assertIn("whitenoise.middleware.WhiteNoiseMiddleware", settings.MIDDLEWARE)
