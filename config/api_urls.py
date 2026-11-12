"""Versioned API URL configuration."""

from django.urls import include, path

urlpatterns = [
    path("auth/", include("apps.accounts.urls.auth")),
    path("users/", include("apps.accounts.urls.users")),
    path("", include("apps.accounts.urls.rbac")),
    path("", include("apps.farms.urls")),
    path("", include("apps.devices.urls")),
    path("", include("apps.telemetry.urls")),
    path("", include("apps.alerts.urls")),
    path("", include("apps.commands.urls")),
    path("", include("apps.simulations.urls")),
    path("sync/", include("apps.sync.urls")),
]
