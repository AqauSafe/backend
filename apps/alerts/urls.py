from rest_framework.routers import DefaultRouter

from apps.alerts.views import AlertRuleViewSet, AlertViewSet

router = DefaultRouter()
router.register("alert-rules", AlertRuleViewSet, basename="alert-rule")
router.register("alerts", AlertViewSet, basename="alert")

urlpatterns = router.urls
