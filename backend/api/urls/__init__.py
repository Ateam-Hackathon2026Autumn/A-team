from django.urls import path

from ..views.health import health


urlpatterns = [
    path("health/", health, name="health"),
]
