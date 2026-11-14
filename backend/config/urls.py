from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),
]

# 開発用：backend/media/ に保存した画像を /media/ で返す（S3 を使わないとき。static() は DEBUG のときだけ有効）
if not settings.USE_S3:
    urlpatterns += static("/media/", document_root=settings.MEDIA_ROOT)

# DEBUG=False のとき、404・500 も共通エラー形式（JSON）で返す
handler404 = "api.common.exceptions.not_found"
handler500 = "api.common.exceptions.server_error"
