"""Alert rule and alert lifecycle views."""

from django.utils import timezone
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.alerts.models import Alert, AlertRule
from apps.alerts.serializers import AlertRuleSerializer, AlertSerializer
from apps.audit.services import log_event
from apps.farms.access import accessible_farms, can_manage_farm, can_write_farm


class AlertRuleViewSet(viewsets.ModelViewSet):
    serializer_class = AlertRuleSerializer
    permission_classes = [IsAuthenticated]
    ordering = ["farm", "metric"]

    def get_queryset(self):
        queryset = AlertRule.objects.filter(
            farm__in=accessible_farms(self.request.user)
        ).select_related("farm", "pond")
        farm_id = self.request.query_params.get("farm_id") or self.request.query_params.get(
            "farmId"
        )
        pond_id = self.request.query_params.get("pond_id") or self.request.query_params.get(
            "pondId"
        )
        if farm_id:
            queryset = queryset.filter(farm_id=farm_id)
        if pond_id:
            queryset = queryset.filter(pond_id=pond_id)
        return queryset

    def perform_create(self, serializer):
        farm = serializer.validated_data["farm"]
        if not can_manage_farm(self.request.user, farm):
            raise PermissionDenied("You cannot manage alert rules for this farm.")
        rule = serializer.save(created_by=self.request.user)
        log_event(
            actor=self.request.user,
            action="alert_rule.created",
            entity_type="alert_rule",
            entity_id=str(rule.id),
            request=self.request,
        )

    def perform_update(self, serializer):
        rule = serializer.instance
        if not can_manage_farm(self.request.user, rule.farm):
            raise PermissionDenied("You cannot manage this alert rule.")
        target_farm = serializer.validated_data.get("farm", rule.farm)
        if not can_manage_farm(self.request.user, target_farm):
            raise ValidationError({"farmId": "You cannot move a rule to that farm."})
        rule = serializer.save()
        log_event(
            actor=self.request.user,
            action="alert_rule.updated",
            entity_type="alert_rule",
            entity_id=str(rule.id),
            request=self.request,
        )

    def perform_destroy(self, instance):
        if not can_manage_farm(self.request.user, instance.farm):
            raise PermissionDenied("You cannot manage this alert rule.")
        log_event(
            actor=self.request.user,
            action="alert_rule.deleted",
            entity_type="alert_rule",
            entity_id=str(instance.id),
            request=self.request,
        )
        instance.delete()


class AlertViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = AlertSerializer
    permission_classes = [IsAuthenticated]
    ordering = ["-triggered_at"]

    def get_queryset(self):
        queryset = Alert.objects.filter(
            farm__in=accessible_farms(self.request.user)
        ).select_related("farm", "pond", "rule", "device", "reading")
        params = self.request.query_params
        farm_id = params.get("farm_id") or params.get("farmId")
        pond_id = params.get("pond_id") or params.get("pondId")
        status_value = params.get("status")
        severity = params.get("severity")
        if farm_id:
            queryset = queryset.filter(farm_id=farm_id)
        if pond_id:
            queryset = queryset.filter(pond_id=pond_id)
        if status_value:
            queryset = queryset.filter(status=status_value)
        if severity:
            queryset = queryset.filter(severity=severity)
        return queryset

    def _get_alert(self, pk):
        alert = self.get_queryset().filter(pk=pk).first()
        if alert is None:
            raise PermissionDenied("Alert not found.")
        if not can_write_farm(self.request.user, alert.farm):
            raise PermissionDenied("You cannot update this alert.")
        return alert

    @action(detail=True, methods=["post"])
    def acknowledge(self, request, pk=None):
        alert = self._get_alert(pk)
        if alert.status == Alert.Status.RESOLVED:
            raise ValidationError("A resolved alert cannot be acknowledged.")
        alert.status = Alert.Status.ACKNOWLEDGED
        alert.acknowledged_at = timezone.now()
        alert.acknowledged_by = request.user
        alert.save(update_fields=["status", "acknowledged_at", "acknowledged_by", "updated_at"])
        log_event(
            actor=request.user,
            action="alert.acknowledged",
            entity_type="alert",
            entity_id=str(alert.id),
            request=request,
        )
        return Response({"data": self.get_serializer(alert).data})

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        alert = self._get_alert(pk)
        alert.status = Alert.Status.RESOLVED
        alert.resolved_at = timezone.now()
        alert.save(update_fields=["status", "resolved_at", "updated_at"])
        log_event(
            actor=request.user,
            action="alert.resolved",
            entity_type="alert",
            entity_id=str(alert.id),
            request=request,
        )
        return Response({"data": self.get_serializer(alert).data})
