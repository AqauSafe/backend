from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.telemetry.views import (
    DashboardSummaryView,
    DeviceEventViewSet,
    DeviceHeartbeatViewSet,
    SensorReadingViewSet,
)

router = DefaultRouter()
router.register("readings", SensorReadingViewSet, basename="reading")
router.register("heartbeats", DeviceHeartbeatViewSet, basename="heartbeat")
router.register("events", DeviceEventViewSet, basename="device-event")

urlpatterns = [
    path("dashboard/summary/", DashboardSummaryView.as_view(), name="dashboard-summary"),
    *router.urls,
]
