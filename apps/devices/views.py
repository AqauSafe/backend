"""Device registry API views."""

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.services import log_event
from apps.common.camel import camelize
from apps.devices.models import Actuator, Device, Sensor
from apps.devices.provisioning import claim_device, device_topics, issue_claim_token
from apps.devices.serializers import (
    ActuatorSerializer,
    ClaimDeviceSerializer,
    DeviceSerializer,
    SensorSerializer,
)
from apps.farms.access import accessible_farms, can_manage_farm, can_write_farm
from integrations.mqtt.publishing import publish_message
from integrations.mqtt.topics import config_topic


class MQTTUnavailable(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "The MQTT broker is unavailable."
    default_code = "mqtt_unavailable"


class DeviceViewSet(viewsets.ModelViewSet):
    serializer_class = DeviceSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ["name", "device_id", "hardware_model"]
    ordering_fields = ["name", "status", "created_at", "last_seen_at"]
    ordering = ["name"]

    def get_queryset(self):
        queryset = Device.objects.filter(
            farm__in=accessible_farms(self.request.user)
        ).select_related("farm", "pond")
        farm_id = self.request.query_params.get("farm_id") or self.request.query_params.get(
            "farmId"
        )
        pond_id = self.request.query_params.get("pond_id") or self.request.query_params.get(
            "pondId"
        )
        status_value = self.request.query_params.get("status")
        if farm_id:
            queryset = queryset.filter(farm_id=farm_id)
        if pond_id:
            queryset = queryset.filter(pond_id=pond_id)
        if status_value:
            queryset = queryset.filter(status=status_value)
        return queryset

    def perform_create(self, serializer):
        farm = serializer.validated_data["farm"]
        if not can_write_farm(self.request.user, farm):
            raise PermissionDenied("You cannot add devices to this farm.")
        device = serializer.save()
        log_event(
            actor=self.request.user,
            action="device.created",
            entity_type="device",
            entity_id=str(device.id),
            request=self.request,
        )

    def perform_update(self, serializer):
        device = serializer.instance
        if not can_write_farm(self.request.user, device.farm):
            raise PermissionDenied("You cannot manage this device.")
        target_farm = serializer.validated_data.get("farm", device.farm)
        if not can_write_farm(self.request.user, target_farm):
            raise ValidationError({"farmId": "You cannot move a device to that farm."})
        device = serializer.save()
        log_event(
            actor=self.request.user,
            action="device.updated",
            entity_type="device",
            entity_id=str(device.id),
            request=self.request,
        )

    def perform_destroy(self, instance):
        if not can_write_farm(self.request.user, instance.farm):
            raise PermissionDenied("You cannot manage this device.")
        log_event(
            actor=self.request.user,
            action="device.deleted",
            entity_type="device",
            entity_id=str(instance.id),
            request=self.request,
        )
        instance.delete()

    @extend_schema(request=None, responses={200: OpenApiTypes.OBJECT})
    @action(detail=True, methods=["post"], url_path="provision")
    def provision(self, request, pk=None):
        device = self.get_object()
        if not can_manage_farm(request.user, device.farm):
            raise PermissionDenied("You cannot provision this device.")
        token = issue_claim_token(device)
        log_event(
            actor=request.user,
            action="device.provisioning_token_issued",
            entity_type="device",
            entity_id=str(device.id),
            request=request,
        )
        return Response(
            {
                "data": {
                    "device_id": device.device_id,
                    "claim_token": token,
                    "claim_expires_at": device.claim_expires_at,
                    "topics": device_topics(device),
                }
            }
        )

    @extend_schema(request=OpenApiTypes.OBJECT, responses={200: OpenApiTypes.OBJECT})
    @action(detail=True, methods=["post"], url_path="config")
    def publish_config(self, request, pk=None):
        device = self.get_object()
        if not can_manage_farm(request.user, device.farm):
            raise PermissionDenied("You cannot configure this device.")
        config = request.data.get("config", request.data)
        if not isinstance(config, dict):
            raise ValidationError({"config": "Configuration must be a JSON object."})
        version = device.config_version + 1
        try:
            publish_message(
                config_topic(device.device_id),
                {"version": version, "config": camelize(config)},
                qos=1,
            )
        except Exception as exc:  # noqa: BLE001
            raise MQTTUnavailable(f"Unable to publish configuration: {exc}") from exc
        device.config = config
        device.config_version = version
        device.save(update_fields=["config", "config_version", "updated_at"])
        log_event(
            actor=request.user,
            action="device.config_published",
            entity_type="device",
            entity_id=str(device.id),
            metadata={"version": version},
            request=request,
        )
        return Response(
            {
                "data": {
                    "device_id": device.device_id,
                    "version": version,
                    "config": device.config,
                }
            }
        )


class DeviceClaimView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]
    throttle_scope = "provision"

    @extend_schema(request=ClaimDeviceSerializer, responses={200: OpenApiTypes.OBJECT})
    def post(self, request):
        serializer = ClaimDeviceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        device, password, command_secret = claim_device(
            serializer.validated_data["device_id"],
            serializer.validated_data["claim_token"],
        )
        log_event(
            actor=None,
            action="device.claimed",
            entity_type="device",
            entity_id=str(device.id),
            request=request,
        )
        return Response(
            {
                "data": {
                    "device_id": device.device_id,
                    "mqtt_username": device.device_id,
                    "mqtt_password": password,
                    "command_secret": command_secret,
                    "provisioned_at": device.provisioned_at,
                    "topics": device_topics(device),
                }
            },
            status=status.HTTP_200_OK,
        )


class SensorViewSet(viewsets.ModelViewSet):
    serializer_class = SensorSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ["name", "key", "sensor_type"]
    ordering = ["device", "name"]

    def get_queryset(self):
        queryset = Sensor.objects.filter(
            device__farm__in=accessible_farms(self.request.user)
        ).select_related("device", "device__farm")
        device_id = self.request.query_params.get("device_id") or self.request.query_params.get(
            "deviceId"
        )
        if device_id:
            queryset = queryset.filter(device_id=device_id)
        return queryset

    def perform_create(self, serializer):
        device = serializer.validated_data["device"]
        if not can_write_farm(self.request.user, device.farm):
            raise PermissionDenied("You cannot add sensors to this device.")
        sensor = serializer.save()
        log_event(
            actor=self.request.user,
            action="sensor.created",
            entity_type="sensor",
            entity_id=str(sensor.id),
            request=self.request,
        )

    def perform_update(self, serializer):
        sensor = serializer.instance
        if not can_write_farm(self.request.user, sensor.device.farm):
            raise PermissionDenied("You cannot manage this sensor.")
        target_device = serializer.validated_data.get("device", sensor.device)
        if not can_write_farm(self.request.user, target_device.farm):
            raise ValidationError({"deviceId": "You cannot move a sensor to that device."})
        sensor = serializer.save()
        log_event(
            actor=self.request.user,
            action="sensor.updated",
            entity_type="sensor",
            entity_id=str(sensor.id),
            request=self.request,
        )

    def perform_destroy(self, instance):
        if not can_write_farm(self.request.user, instance.device.farm):
            raise PermissionDenied("You cannot manage this sensor.")
        log_event(
            actor=self.request.user,
            action="sensor.deleted",
            entity_type="sensor",
            entity_id=str(instance.id),
            request=self.request,
        )
        instance.delete()


class ActuatorViewSet(viewsets.ModelViewSet):
    serializer_class = ActuatorSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ["name", "key", "actuator_type"]
    ordering = ["device", "name"]

    def get_queryset(self):
        queryset = Actuator.objects.filter(
            device__farm__in=accessible_farms(self.request.user)
        ).select_related("device", "device__farm")
        device_id = self.request.query_params.get("device_id") or self.request.query_params.get(
            "deviceId"
        )
        if device_id:
            queryset = queryset.filter(device_id=device_id)
        return queryset

    def perform_create(self, serializer):
        device = serializer.validated_data["device"]
        if not can_write_farm(self.request.user, device.farm):
            raise PermissionDenied("You cannot add actuators to this device.")
        actuator = serializer.save()
        log_event(
            actor=self.request.user,
            action="actuator.created",
            entity_type="actuator",
            entity_id=str(actuator.id),
            request=self.request,
        )

    def perform_update(self, serializer):
        actuator = serializer.instance
        if not can_write_farm(self.request.user, actuator.device.farm):
            raise PermissionDenied("You cannot manage this actuator.")
        target_device = serializer.validated_data.get("device", actuator.device)
        if not can_write_farm(self.request.user, target_device.farm):
            raise ValidationError({"deviceId": "You cannot move an actuator to that device."})
        actuator = serializer.save()
        log_event(
            actor=self.request.user,
            action="actuator.updated",
            entity_type="actuator",
            entity_id=str(actuator.id),
            request=self.request,
        )

    def perform_destroy(self, instance):
        if not can_write_farm(self.request.user, instance.device.farm):
            raise PermissionDenied("You cannot manage this actuator.")
        log_event(
            actor=self.request.user,
            action="actuator.deleted",
            entity_type="actuator",
            entity_id=str(instance.id),
            request=self.request,
        )
        instance.delete()
