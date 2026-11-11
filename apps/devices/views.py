"""Device registry API views."""

from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated

from apps.audit.services import log_event
from apps.devices.models import Actuator, Device, Sensor
from apps.devices.serializers import ActuatorSerializer, DeviceSerializer, SensorSerializer
from apps.farms.access import accessible_farms, can_write_farm


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
