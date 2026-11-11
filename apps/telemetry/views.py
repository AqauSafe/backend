"""Telemetry and dashboard API views."""

from django.db.models import Count, Q
from django.utils.dateparse import parse_datetime
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.alerts.models import Alert
from apps.alerts.services import evaluate_reading
from apps.audit.services import log_event
from apps.devices.models import Device
from apps.farms.access import accessible_farms, accessible_ponds, can_write_pond
from apps.telemetry.models import DeviceEvent, DeviceHeartbeat, SensorReading
from apps.telemetry.serializers import (
    DeviceEventSerializer,
    DeviceHeartbeatSerializer,
    SensorReadingSerializer,
)


class SensorReadingViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = SensorReadingSerializer
    permission_classes = [IsAuthenticated]
    ordering_fields = ["recorded_at", "received_at", "created_at"]
    ordering = ["-recorded_at"]

    def get_queryset(self):
        queryset = SensorReading.objects.filter(
            pond__in=accessible_ponds(self.request.user)
        ).select_related("pond", "pond__farm", "device", "sensor")
        params = self.request.query_params
        pond_id = params.get("pond_id") or params.get("pondId")
        farm_id = params.get("farm_id") or params.get("farmId")
        device_id = params.get("device_id") or params.get("deviceId")
        source = params.get("source")
        recorded_after = params.get("recorded_after") or params.get("from")
        recorded_before = params.get("recorded_before") or params.get("to")

        if pond_id:
            queryset = queryset.filter(pond_id=pond_id)
        if farm_id:
            queryset = queryset.filter(pond__farm_id=farm_id)
        if device_id:
            queryset = queryset.filter(device_id=device_id)
        if source:
            queryset = queryset.filter(source=source)
        if recorded_after:
            value = parse_datetime(recorded_after)
            if value is None:
                raise ValidationError({"from": "Use an ISO-8601 datetime."})
            queryset = queryset.filter(recorded_at__gte=value)
        if recorded_before:
            value = parse_datetime(recorded_before)
            if value is None:
                raise ValidationError({"to": "Use an ISO-8601 datetime."})
            queryset = queryset.filter(recorded_at__lte=value)
        return queryset

    def perform_create(self, serializer):
        pond = serializer.validated_data["pond"]
        if not can_write_pond(self.request.user, pond):
            raise PermissionDenied("You cannot add readings to this pond.")
        reading = serializer.save()
        evaluate_reading(reading)
        log_event(
            actor=self.request.user,
            action="reading.created",
            entity_type="sensor_reading",
            entity_id=str(reading.id),
            metadata={"source": reading.source, "pondId": str(reading.pond_id)},
            request=self.request,
        )

    @action(detail=False, methods=["get"], url_path="latest")
    def latest(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        pond_id = request.query_params.get("pond_id") or request.query_params.get("pondId")
        if pond_id:
            reading = queryset.filter(pond_id=pond_id).first()
            if reading is None:
                return Response({"data": None})
            return Response({"data": self.get_serializer(reading).data})

        readings = []
        seen = set()
        for reading in queryset:
            if reading.pond_id in seen:
                continue
            seen.add(reading.pond_id)
            readings.append(reading)
        return Response({"data": self.get_serializer(readings, many=True).data})


class DeviceHeartbeatViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    serializer_class = DeviceHeartbeatSerializer
    permission_classes = [IsAuthenticated]
    ordering = ["-recorded_at"]

    def get_queryset(self):
        queryset = DeviceHeartbeat.objects.filter(
            device__farm__in=accessible_farms(self.request.user)
        ).select_related("device")
        device_id = self.request.query_params.get("device_id") or self.request.query_params.get(
            "deviceId"
        )
        if device_id:
            queryset = queryset.filter(device_id=device_id)
        return queryset


class DeviceEventViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = DeviceEventSerializer
    permission_classes = [IsAuthenticated]
    ordering = ["-recorded_at"]

    def get_queryset(self):
        queryset = DeviceEvent.objects.filter(
            device__farm__in=accessible_farms(self.request.user)
        ).select_related("device")
        device_id = self.request.query_params.get("device_id") or self.request.query_params.get(
            "deviceId"
        )
        severity = self.request.query_params.get("severity")
        if device_id:
            queryset = queryset.filter(device_id=device_id)
        if severity:
            queryset = queryset.filter(severity=severity)
        return queryset


class DashboardSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        farms = accessible_farms(request.user)
        ponds = accessible_ponds(request.user)
        devices = Device.objects.filter(farm__in=farms)
        readings = SensorReading.objects.filter(pond__in=ponds)

        latest_readings = []
        for pond in ponds.select_related("farm"):
            reading = readings.filter(pond=pond).first()
            if reading:
                latest_readings.append(SensorReadingSerializer(reading).data)

        alerts = Alert.objects.filter(
            farm__in=farms, status__in=[Alert.Status.ACTIVE, Alert.Status.ACKNOWLEDGED]
        ).select_related("farm", "pond")
        severity_counts = alerts.aggregate(
            active=Count("id", filter=Q(status=Alert.Status.ACTIVE)),
            critical=Count("id", filter=Q(severity="critical")),
            warning=Count("id", filter=Q(severity="warning")),
        )

        return Response(
            {
                "data": {
                    "farms": farms.count(),
                    "ponds": ponds.count(),
                    "devices": devices.count(),
                    "devicesOnline": devices.filter(status=Device.Status.ONLINE).count(),
                    "readings": readings.count(),
                    "latestReadings": latest_readings,
                    "activeAlerts": severity_counts["active"],
                    "criticalAlerts": severity_counts["critical"],
                    "warningAlerts": severity_counts["warning"],
                }
            },
            status=status.HTTP_200_OK,
        )
