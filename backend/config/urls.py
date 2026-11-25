from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path


urlpatterns = []

# Django 標準の管理画面（marche/admin.py）。CloudFront は /api/* だけをバックエンドに流すので /api/ の下に置く。
# 本番（DEBUG=false）は環境変数 DJANGO_ADMIN_ENABLED=true のときだけ開ける
if settings.DJANGO_ADMIN_ENABLED:
    urlpatterns.append(path("api/django-admin/", admin.site.urls))

urlpatterns.append(path("api/", include("api.urls")))

# 開発用：backend/media/ に保存した画像を /media/ で返す（S3 を使わないとき。static() は DEBUG のときだけ有効）
if not settings.USE_S3:
    urlpatterns += static("/media/", document_root=settings.MEDIA_ROOT)

# DEBUG=False のとき、404・500 も共通エラー形式（JSON）で返す
handler404 = "api.common.exceptions.not_found"
handler500 = "api.common.exceptions.server_error"
