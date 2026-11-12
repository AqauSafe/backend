"""Device registry serializers."""

from rest_framework import serializers

from apps.devices.models import Actuator, Device, Sensor
from apps.farms.models import Farm, Pond


class DeviceSerializer(serializers.ModelSerializer):
    farm_id = serializers.PrimaryKeyRelatedField(source="farm", queryset=Farm.objects.all())
    pond_id = serializers.PrimaryKeyRelatedField(
        source="pond",
        queryset=Pond.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Device
        fields = (
            "id",
            "farm_id",
            "pond_id",
            "device_id",
            "name",
            "kind",
            "status",
            "hardware_model",
            "firmware_version",
            "last_seen_at",
            "claim_expires_at",
            "provisioned_at",
            "config_version",
            "config",
            "client_id",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "last_seen_at",
            "claim_expires_at",
            "provisioned_at",
            "config_version",
            "config",
            "created_at",
            "updated_at",
        )
        validators = []

    def validate(self, attrs):
        farm = attrs.get("farm") or getattr(self.instance, "farm", None)
        pond = attrs.get("pond") if "pond" in attrs else getattr(self.instance, "pond", None)
        if pond and farm and pond.farm_id != farm.id:
            raise serializers.ValidationError({"pondId": "Pond belongs to another farm."})
        return attrs


class SensorSerializer(serializers.ModelSerializer):
    device_id = serializers.PrimaryKeyRelatedField(source="device", queryset=Device.objects.all())

    class Meta:
        model = Sensor
        fields = (
            "id",
            "device_id",
            "key",
            "name",
            "sensor_type",
            "unit",
            "pin",
            "calibration",
            "is_active",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class ActuatorSerializer(serializers.ModelSerializer):
    device_id = serializers.PrimaryKeyRelatedField(source="device", queryset=Device.objects.all())

    class Meta:
        model = Actuator
        fields = (
            "id",
            "device_id",
            "key",
            "name",
            "actuator_type",
            "pin",
            "is_active",
            "state",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class ClaimDeviceSerializer(serializers.Serializer):
    device_id = serializers.CharField(max_length=100)
    claim_token = serializers.CharField(max_length=200, trim_whitespace=False)
