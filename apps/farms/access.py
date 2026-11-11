"""Farm-scoped authorization helpers."""

from django.db.models import Q

from apps.farms.models import Farm, FarmMembership, Pond

MANAGER_ROLES = {FarmMembership.Role.OWNER, FarmMembership.Role.MANAGER}
WRITE_ROLES = {FarmMembership.Role.OWNER, FarmMembership.Role.MANAGER, FarmMembership.Role.WORKER}


def accessible_farms(user):
    if not getattr(user, "is_authenticated", False):
        return Farm.objects.none()
    if user.is_superuser:
        return Farm.objects.all()
    return Farm.objects.filter(Q(owner=user) | Q(memberships__user=user)).distinct()


def accessible_ponds(user):
    return Pond.objects.filter(farm__in=accessible_farms(user))


def membership_for(user, farm: Farm) -> FarmMembership | None:
    if not getattr(user, "is_authenticated", False):
        return None
    return farm.memberships.filter(user=user).first()


def can_view_farm(user, farm: Farm) -> bool:
    return getattr(user, "is_authenticated", False) and (
        user.is_superuser or farm.owner_id == user.id or membership_for(user, farm) is not None
    )


def can_manage_farm(user, farm: Farm) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser or farm.owner_id == user.id:
        return True
    membership = membership_for(user, farm)
    return membership is not None and membership.role in MANAGER_ROLES


def can_write_farm(user, farm: Farm) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser or farm.owner_id == user.id:
        return True
    membership = membership_for(user, farm)
    return membership is not None and membership.role in WRITE_ROLES


def can_write_pond(user, pond: Pond) -> bool:
    return can_write_farm(user, pond.farm)
