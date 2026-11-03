from django.urls import include, path

from ..views.health import health


urlpatterns = [
    path("health/", health, name="health"),
    # /api/v1/admin/... は管理者APIのステップで追加する
    path("v1/dashboard/", include("api.urls.dashboard")),
    path("v1/", include("api.urls.public")),
]
