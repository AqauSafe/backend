from rest_framework.routers import DefaultRouter

from apps.commands.views import CommandViewSet

router = DefaultRouter()
router.register("commands", CommandViewSet, basename="command")

urlpatterns = router.urls
