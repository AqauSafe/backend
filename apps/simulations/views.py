"""Simulation history and live-state APIs."""

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.services import log_event
from apps.farms.access import accessible_farms, accessible_ponds, can_write_pond
from apps.simulations.models import Simulation, SimulationRun
from apps.simulations.serializers import (
    SimulationRunInputSerializer,
    SimulationRunSerializer,
    SimulationSerializer,
    SimulationStateInputSerializer,
)
from apps.simulations.services import ingest_simulation_state
from apps.telemetry.realtime import broadcast_farm_event
from apps.telemetry.serializers import SensorReadingSerializer


class SimulationRunViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "create":
            return SimulationRunInputSerializer
        return SimulationRunSerializer

    def get_queryset(self):
        queryset = SimulationRun.objects.filter(
            farm__in=accessible_farms(self.request.user)
        ).select_related("farm", "pond")
        params = self.request.query_params
        pond_id = params.get("pond_id") or params.get("pondId")
        farm_id = params.get("farm_id") or params.get("farmId")
        if pond_id:
            queryset = queryset.filter(pond_id=pond_id)
        if farm_id:
            queryset = queryset.filter(farm_id=farm_id)
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pond = serializer.validated_data["pond"]
        if not can_write_pond(request.user, pond):
            raise PermissionDenied("You cannot run simulations for this pond.")
        run = serializer.save()
        log_event(
            actor=request.user,
            action="simulation.completed",
            entity_type="simulation_run",
            entity_id=str(run.id),
            metadata={"pondId": str(pond.id), "durationDays": run.duration_days},
            request=request,
        )
        payload = SimulationRunSerializer(run).data
        broadcast_farm_event(
            run.farm_id,
            "simulation.completed",
            {"simulationRun": payload},
        )
        return Response(payload, status=status.HTTP_201_CREATED)


class SimulationStateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        pond_id = request.query_params.get("pond_id") or request.query_params.get("pondId")
        if not pond_id:
            simulations = Simulation.objects.filter(
                farm__in=accessible_farms(request.user)
            ).select_related("farm", "pond")
            return Response({"data": SimulationSerializer(simulations, many=True).data})

        simulation = (
            Simulation.objects.filter(pond__in=accessible_ponds(request.user), pond_id=pond_id)
            .select_related("farm", "pond")
            .first()
        )
        if simulation is None:
            raise NotFound("No simulation state exists for this pond.")
        return Response({"data": SimulationSerializer(simulation).data})

    @extend_schema(
        request=SimulationStateInputSerializer,
        responses={201: OpenApiTypes.OBJECT},
    )
    def post(self, request):
        serializer = SimulationStateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        pond = data.pop("pond")
        if not can_write_pond(request.user, pond):
            raise PermissionDenied("You cannot update simulations for this pond.")
        values = {
            field: data.pop(field)
            for field in ("temperature", "oxygen", "ph", "level", "turbidity_ntu")
            if field in data
        }
        simulation, reading = ingest_simulation_state(
            pond=pond,
            values=values,
            recorded_at=data.get("recorded_at"),
            client_id=data.get("client_id", ""),
            message_id=data.get("message_id", ""),
            raw=values,
        )
        log_event(
            actor=request.user,
            action="simulation.state_received",
            entity_type="simulation",
            entity_id=str(simulation.id),
            metadata={"pondId": str(pond.id), "readingId": str(reading.id)},
            request=request,
        )
        return Response(
            {
                "simulation": SimulationSerializer(simulation).data,
                "reading": SensorReadingSerializer(reading).data,
            },
            status=status.HTTP_201_CREATED,
        )
