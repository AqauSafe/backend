"""Alert serializers."""

from rest_framework import serializers

from apps.alerts.models import Alert, AlertRule
from apps.farms.models import Farm, Pond


class AlertRuleSerializer(serializers.ModelSerializer):
    farm_id = serializers.PrimaryKeyRelatedField(source="farm", queryset=Farm.objects.all())
    pond_id = serializers.PrimaryKeyRelatedField(
        source="pond",
        queryset=Pond.objects.all(),
        required=False,
        allow_null=True,
    )
    created_by_id = serializers.UUIDField(source="created_by.id", read_only=True)

    class Meta:
        model = AlertRule
        fields = (
            "id",
            "farm_id",
            "pond_id",
            "metric",
            "operator",
            "threshold",
            "severity",
            "cooldown_minutes",
            "is_active",
            "created_by_id",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_by_id", "created_at", "updated_at")

    def validate(self, attrs):
        farm = attrs.get("farm") or getattr(self.instance, "farm", None)
        pond = attrs.get("pond") if "pond" in attrs else getattr(self.instance, "pond", None)
        if pond and farm and pond.farm_id != farm.id:
            raise serializers.ValidationError({"pondId": "Pond belongs to another farm."})
        return attrs


class AlertSerializer(serializers.ModelSerializer):
    farm_id = serializers.UUIDField(read_only=True)
    pond_id = serializers.UUIDField(read_only=True, allow_null=True)
    rule_id = serializers.UUIDField(read_only=True, allow_null=True)
    device_id = serializers.UUIDField(read_only=True, allow_null=True)
    reading_id = serializers.UUIDField(read_only=True, allow_null=True)
    acknowledged_by_id = serializers.UUIDField(read_only=True, allow_null=True)

    class Meta:
        model = Alert
        fields = (
            "id",
            "farm_id",
            "pond_id",
            "rule_id",
            "device_id",
            "reading_id",
            "metric",
            "value",
            "threshold",
            "severity",
            "status",
            "message",
            "triggered_at",
            "acknowledged_at",
            "acknowledged_by_id",
            "resolved_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields
