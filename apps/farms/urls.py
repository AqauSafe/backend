from rest_framework.routers import DefaultRouter

from apps.farms.views import FarmViewSet, FeedingViewSet, PondViewSet

router = DefaultRouter()
router.register("farms", FarmViewSet, basename="farm")
router.register("ponds", PondViewSet, basename="pond")
router.register("feedings", FeedingViewSet, basename="feeding")

urlpatterns = router.urls
