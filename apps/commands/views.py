"""Device command API views."""

from rest_framework import mixins, status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.audit.services import log_event
from apps.commands.models import Command
from apps.commands.serializers import CommandCreateSerializer, CommandSerializer
from apps.commands.services import create_command
from apps.farms.access import accessible_farms, can_manage_farm


class CommandViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return CommandCreateSerializer
        return CommandSerializer

    def get_queryset(self):
        queryset = Command.objects.filter(
            device__farm__in=accessible_farms(self.request.user)
        ).select_related("device", "device__farm", "issued_by")
        device_id = self.request.query_params.get("device_id") or self.request.query_params.get(
            "deviceId"
        )
        status_value = self.request.query_params.get("status")
        if device_id:
            queryset = queryset.filter(device_id=device_id)
        if status_value:
            queryset = queryset.filter(status=status_value)
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        device = serializer.validated_data["device"]
        if not can_manage_farm(request.user, device.farm):
            raise PermissionDenied("You cannot command this device.")
        command = create_command(
            device=device,
            actor=request.user,
            command_type=serializer.validated_data["command_type"],
            payload=serializer.validated_data.get("payload") or {},
            ttl_seconds=serializer.validated_data.get("ttl_seconds", 60),
        )
        log_event(
            actor=request.user,
            action="command.created",
            entity_type="command",
            entity_id=str(command.id),
            metadata={"deviceId": device.device_id, "type": command.command_type},
            request=request,
        )
        return Response(
            {"data": CommandSerializer(command).data},
            status=status.HTTP_201_CREATED,
        )
