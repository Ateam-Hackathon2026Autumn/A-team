import os
import subprocess
import sys
from pathlib import Path

from django.test import SimpleTestCase, override_settings
from django.urls import reverse

BACKEND_DIR = Path(__file__).resolve().parents[2]
PRINT_SETTINGS = "import config.settings as s; print(s.DEBUG, getattr(s, 'SECURE_PROXY_SSL_HEADER', None))"


class HealthViewTests(SimpleTestCase):
    def test_health_endpoint(self):
        response = self.client.get(reverse("health"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"status": "ok", "service": "backend"},
        )

    @override_settings(ALLOWED_HOSTS=["api.example.com"])
    def test_health_ignores_host_for_alb(self):
        """ALB は Host に IP アドレスを入れて確認しに来るので、ALLOWED_HOSTS になくても 200"""
        response = self.client.get("/api/health/", HTTP_HOST="10.0.1.23:8000")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "no-store")
        # ほかの URL は今までどおり 400
        self.assertEqual(self.client.get("/api/v1/categories", HTTP_HOST="10.0.1.23:8000").status_code, 400)


class ProductionSettingsTests(SimpleTestCase):
    """DJANGO_DEBUG=false のときの起動時チェック（設定を読み込むだけの別プロセスで確かめる）"""

    def load_settings(self, **environ):
        env = {k: v for k, v in os.environ.items() if not k.startswith("DJANGO_")}
        env.update(environ)
        return subprocess.run(
            [sys.executable, "-c", PRINT_SETTINGS],
            cwd=BACKEND_DIR, env=env, capture_output=True, text=True)

    def test_refuses_dev_secret_key_when_debug_is_false(self):
        for key in ("", "dev-only-secret-key", "hackathon_secret_key", "short"):
            with self.subTest(key=key):
                result = self.load_settings(DJANGO_DEBUG="false", DJANGO_SECRET_KEY=key)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("DJANGO_SECRET_KEY", result.stderr)

    def test_starts_with_production_secret_key(self):
        result = self.load_settings(DJANGO_DEBUG="false", DJANGO_SECRET_KEY="x" * 50)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "False ('HTTP_X_FORWARDED_PROTO', 'https')")

    def test_local_default_is_unchanged(self):
        """DJANGO_DEBUG を渡さない・true のときは、開発用のキーでも起動する（ローカル・テスト）"""
        for environ in ({}, {"DJANGO_DEBUG": "true"}, {"DJANGO_DEBUG": ""}):
            with self.subTest(environ=environ):
                result = self.load_settings(**environ)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue(result.stdout.startswith("True"))
