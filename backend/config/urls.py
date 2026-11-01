from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),
]

# DEBUG=False のとき、404・500 も共通エラー形式（JSON）で返す
handler404 = "api.common.exceptions.not_found"
handler500 = "api.common.exceptions.server_error"
