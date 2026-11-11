from rest_framework.routers import DefaultRouter

from apps.devices.views import ActuatorViewSet, DeviceViewSet, SensorViewSet

router = DefaultRouter()
router.register("devices", DeviceViewSet, basename="device")
router.register("sensors", SensorViewSet, basename="sensor")
router.register("actuators", ActuatorViewSet, basename="actuator")

urlpatterns = router.urls
