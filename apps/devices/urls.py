from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.devices.views import ActuatorViewSet, DeviceClaimView, DeviceViewSet, SensorViewSet

router = DefaultRouter()
router.register("devices", DeviceViewSet, basename="device")
router.register("sensors", SensorViewSet, basename="sensor")
router.register("actuators", ActuatorViewSet, basename="actuator")

urlpatterns = [
    path("devices/claim/", DeviceClaimView.as_view(), name="device-claim"),
    *router.urls,
]
