"""Telemetry serializers."""

from rest_framework import serializers

from apps.devices.models import Device, Sensor
from apps.farms.models import Pond
from apps.telemetry.models import DeviceEvent, DeviceHeartbeat, SensorReading


class SensorReadingSerializer(serializers.ModelSerializer):
    pond_id = serializers.PrimaryKeyRelatedField(source="pond", queryset=Pond.objects.all())
    device_id = serializers.PrimaryKeyRelatedField(
        source="device",
        queryset=Device.objects.all(),
        required=False,
        allow_null=True,
    )
    sensor_id = serializers.PrimaryKeyRelatedField(
        source="sensor",
        queryset=Sensor.objects.all(),
        required=False,
        allow_null=True,
    )
    date = serializers.DateTimeField(source="recorded_at", read_only=True)

    class Meta:
        model = SensorReading
        fields = (
            "id",
            "pond_id",
            "device_id",
            "sensor_id",
            "source",
            "recorded_at",
            "received_at",
            "date",
            "temperature",
            "oxygen",
            "ph",
            "level",
            "client_id",
            "message_id",
            "raw",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "received_at", "date", "created_at", "updated_at")
        validators = []

    def validate(self, attrs):
        instance = self.instance
        pond = attrs.get("pond") or getattr(instance, "pond", None)
        device = attrs.get("device") if "device" in attrs else getattr(instance, "device", None)
        sensor = attrs.get("sensor") if "sensor" in attrs else getattr(instance, "sensor", None)

        measurement_fields = ("temperature", "oxygen", "ph", "level")
        has_measurement = any(
            (attrs.get(field) if field in attrs else getattr(instance, field, None)) is not None
            for field in measurement_fields
        )
        if not has_measurement:
            raise serializers.ValidationError(
                "At least one of temperature, oxygen, pH or level is required."
            )
        if pond and device and device.farm_id != pond.farm_id:
            raise serializers.ValidationError({"deviceId": "Device belongs to another farm."})
        if device and sensor and sensor.device_id != device.id:
            raise serializers.ValidationError({"sensorId": "Sensor belongs to another device."})
        if sensor and not device:
            device = sensor.device
            attrs["device"] = device

        client_id = attrs.get("client_id") or getattr(instance, "client_id", "")
        if pond and client_id:
            queryset = SensorReading.objects.filter(pond=pond, client_id=client_id)
            if instance is not None:
                queryset = queryset.exclude(pk=instance.pk)
            if queryset.exists():
                raise serializers.ValidationError(
                    {"clientId": "This reading was already recorded."}
                )

        message_id = attrs.get("message_id") or getattr(instance, "message_id", "")
        if device and message_id:
            queryset = SensorReading.objects.filter(device=device, message_id=message_id)
            if instance is not None:
                queryset = queryset.exclude(pk=instance.pk)
            if queryset.exists():
                raise serializers.ValidationError(
                    {"messageId": "This device message was already recorded."}
                )
        return attrs


class DeviceHeartbeatSerializer(serializers.ModelSerializer):
    device_id = serializers.PrimaryKeyRelatedField(source="device", queryset=Device.objects.all())

    class Meta:
        model = DeviceHeartbeat
        fields = (
            "id",
            "device_id",
            "recorded_at",
            "received_at",
            "status",
            "rssi",
            "uptime_seconds",
            "metadata",
            "created_at",
        )
        read_only_fields = ("id", "received_at", "created_at")


class DeviceEventSerializer(serializers.ModelSerializer):
    device_id = serializers.PrimaryKeyRelatedField(source="device", queryset=Device.objects.all())

    class Meta:
        model = DeviceEvent
        fields = (
            "id",
            "device_id",
            "event_type",
            "severity",
            "message",
            "recorded_at",
            "received_at",
            "metadata",
            "created_at",
        )
        read_only_fields = ("id", "received_at", "created_at")
