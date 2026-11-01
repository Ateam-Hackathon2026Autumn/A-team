from django.urls import include, path

from ..views.health import health


urlpatterns = [
    path("health/", health, name="health"),
    # /api/v1/dashboard/... と /api/v1/admin/... は、それぞれのステップで追加する
    path("v1/", include("api.urls.public")),
]
