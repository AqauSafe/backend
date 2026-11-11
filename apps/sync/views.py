"""Frontend compatibility sync endpoints."""

from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.serializers import UserSerializer
from apps.alerts.models import Alert
from apps.alerts.serializers import AlertSerializer
from apps.audit.services import log_event
from apps.devices.models import Device
from apps.devices.serializers import DeviceSerializer
from apps.farms.access import accessible_farms, accessible_ponds
from apps.farms.models import Feeding
from apps.farms.serializers import FarmSerializer, FeedingSerializer, PondSerializer
from apps.sync.serializers import SyncImportSerializer
from apps.sync.services import import_app_data
from apps.telemetry.serializers import SensorReadingSerializer


class SyncBootstrapView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        user = request.user
        farms = accessible_farms(user).select_related("owner")
        ponds = accessible_ponds(user).select_related("farm")
        readings = []
        for pond in ponds:
            readings.extend(pond.readings.select_related("pond", "device", "sensor")[:50])
        feedings = Feeding.objects.filter(pond__in=ponds).select_related("pond", "created_by")[:500]
        devices = Device.objects.filter(farm__in=farms).select_related("farm", "pond")
        alerts = Alert.objects.filter(
            farm__in=farms, status__in=[Alert.Status.ACTIVE, Alert.Status.ACKNOWLEDGED]
        ).select_related("farm", "pond", "rule", "device", "reading")

        return Response(
            {
                "data": {
                    "user": UserSerializer(user).data,
                    "language": user.language,
                    "farms": FarmSerializer(farms, many=True).data,
                    "ponds": PondSerializer(ponds, many=True).data,
                    "feedings": FeedingSerializer(feedings, many=True).data,
                    "readings": SensorReadingSerializer(readings, many=True).data,
                    "devices": DeviceSerializer(devices, many=True).data,
                    "alerts": AlertSerializer(alerts, many=True).data,
                    "listings": [],
                    "messages": [],
                    "serverTime": timezone.now().isoformat(),
                }
            }
        )


class SyncImportView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "telemetry"

    @extend_schema(request=SyncImportSerializer, responses={200: OpenApiTypes.OBJECT})
    def post(self, request):
        serializer = SyncImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        summary = import_app_data(request.user, serializer.validated_data)
        log_event(
            actor=request.user,
            action="sync.imported",
            entity_type="sync",
            metadata={
                "farms": summary["farms"],
                "ponds": summary["ponds"],
                "feedings": summary["feedings"],
                "readings": summary["readings"],
                "errors": len(summary["errors"]),
            },
            request=request,
        )
        return Response({"data": summary})
