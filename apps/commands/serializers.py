"""Device command serializers."""

from rest_framework import serializers

from apps.commands.models import Command
from apps.devices.models import Device


class CommandSerializer(serializers.ModelSerializer):
    device_id = serializers.UUIDField(read_only=True)
    issued_by_id = serializers.UUIDField(read_only=True, allow_null=True)

    class Meta:
        model = Command
        fields = (
            "id",
            "device_id",
            "issued_by_id",
            "command_type",
            "payload",
            "status",
            "signature",
            "expires_at",
            "sent_at",
            "acknowledged_at",
            "result",
            "error",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class CommandCreateSerializer(serializers.Serializer):
    device_id = serializers.PrimaryKeyRelatedField(source="device", queryset=Device.objects.all())
    command_type = serializers.CharField(max_length=50)
    payload = serializers.JSONField(default=dict)
    ttl_seconds = serializers.IntegerField(default=60, min_value=5, max_value=3600)
