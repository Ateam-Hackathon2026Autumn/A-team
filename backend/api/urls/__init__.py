from django.urls import include, path

from ..views.health import health


urlpatterns = [
    path("health/", health, name="health"),
    # 管理者向けAPI
    path("v1/admin/", include("api.urls.admin")),
    path("v1/dashboard/", include("api.urls.dashboard")),
    path("v1/", include("api.urls.public")),
]
