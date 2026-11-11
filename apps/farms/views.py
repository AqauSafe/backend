"""Farm, pond and feeding API views."""

from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated

from apps.audit.services import log_event
from apps.farms.access import (
    accessible_farms,
    accessible_ponds,
    can_manage_farm,
    can_write_farm,
    can_write_pond,
)
from apps.farms.models import FarmMembership, Feeding
from apps.farms.serializers import FarmSerializer, FeedingSerializer, PondSerializer


class FarmViewSet(viewsets.ModelViewSet):
    serializer_class = FarmSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ["name", "location"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]

    def get_queryset(self):
        return accessible_farms(self.request.user).prefetch_related("memberships")

    def perform_create(self, serializer):
        farm = serializer.save(owner=self.request.user)
        FarmMembership.objects.get_or_create(
            farm=farm,
            user=self.request.user,
            defaults={"role": FarmMembership.Role.OWNER},
        )
        log_event(
            actor=self.request.user,
            action="farm.created",
            entity_type="farm",
            entity_id=str(farm.id),
            request=self.request,
        )

    def perform_update(self, serializer):
        if not can_manage_farm(self.request.user, serializer.instance):
            raise PermissionDenied("You cannot manage this farm.")
        farm = serializer.save()
        log_event(
            actor=self.request.user,
            action="farm.updated",
            entity_type="farm",
            entity_id=str(farm.id),
            request=self.request,
        )

    def perform_destroy(self, instance):
        if not can_manage_farm(self.request.user, instance):
            raise PermissionDenied("You cannot manage this farm.")
        log_event(
            actor=self.request.user,
            action="farm.deleted",
            entity_type="farm",
            entity_id=str(instance.id),
            request=self.request,
        )
        instance.delete()


class PondViewSet(viewsets.ModelViewSet):
    serializer_class = PondSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ["name", "species"]
    ordering_fields = ["name", "population", "created_at"]
    ordering = ["name"]

    def get_queryset(self):
        queryset = accessible_ponds(self.request.user).select_related("farm")
        farm_id = self.request.query_params.get("farm_id") or self.request.query_params.get(
            "farmId"
        )
        if farm_id:
            queryset = queryset.filter(farm_id=farm_id)
        return queryset

    def perform_create(self, serializer):
        farm = serializer.validated_data["farm"]
        if not can_write_farm(self.request.user, farm):
            raise PermissionDenied("You cannot add ponds to this farm.")
        pond = serializer.save()
        log_event(
            actor=self.request.user,
            action="pond.created",
            entity_type="pond",
            entity_id=str(pond.id),
            request=self.request,
        )

    def perform_update(self, serializer):
        pond = serializer.instance
        if not can_write_pond(self.request.user, pond):
            raise PermissionDenied("You cannot manage this pond.")
        target_farm = serializer.validated_data.get("farm", pond.farm)
        if target_farm.id != pond.farm_id and not can_manage_farm(self.request.user, target_farm):
            raise ValidationError({"farmId": "You cannot move a pond to that farm."})
        pond = serializer.save()
        log_event(
            actor=self.request.user,
            action="pond.updated",
            entity_type="pond",
            entity_id=str(pond.id),
            request=self.request,
        )

    def perform_destroy(self, instance):
        if not can_write_pond(self.request.user, instance):
            raise PermissionDenied("You cannot manage this pond.")
        log_event(
            actor=self.request.user,
            action="pond.deleted",
            entity_type="pond",
            entity_id=str(instance.id),
            request=self.request,
        )
        instance.delete()


class FeedingViewSet(viewsets.ModelViewSet):
    serializer_class = FeedingSerializer
    permission_classes = [IsAuthenticated]
    ordering_fields = ["fed_at", "amount", "created_at"]
    ordering = ["-fed_at"]

    def get_queryset(self):
        queryset = Feeding.objects.filter(
            pond__in=accessible_ponds(self.request.user)
        ).select_related("pond", "created_by")
        pond_id = self.request.query_params.get("pond_id") or self.request.query_params.get(
            "pondId"
        )
        if pond_id:
            queryset = queryset.filter(pond_id=pond_id)
        return queryset

    def perform_create(self, serializer):
        pond = serializer.validated_data["pond"]
        if not can_write_pond(self.request.user, pond):
            raise PermissionDenied("You cannot record feeding for this pond.")
        feeding = serializer.save(created_by=self.request.user)
        log_event(
            actor=self.request.user,
            action="feeding.created",
            entity_type="feeding",
            entity_id=str(feeding.id),
            request=self.request,
        )

    def perform_update(self, serializer):
        feeding = serializer.instance
        if not can_write_pond(self.request.user, feeding.pond):
            raise PermissionDenied("You cannot manage this feeding record.")
        target_pond = serializer.validated_data.get("pond", feeding.pond)
        if not can_write_pond(self.request.user, target_pond):
            raise ValidationError({"pondId": "You cannot move feeding to that pond."})
        feeding = serializer.save()
        log_event(
            actor=self.request.user,
            action="feeding.updated",
            entity_type="feeding",
            entity_id=str(feeding.id),
            request=self.request,
        )

    def perform_destroy(self, instance):
        if not can_write_pond(self.request.user, instance.pond):
            raise PermissionDenied("You cannot manage this feeding record.")
        log_event(
            actor=self.request.user,
            action="feeding.deleted",
            entity_type="feeding",
            entity_id=str(instance.id),
            request=self.request,
        )
        instance.delete()
