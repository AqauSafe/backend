"""Role group definitions and helpers."""

from django.contrib.auth.models import Group

from apps.accounts.models import UserRole

ROLE_GROUP_NAMES = {
    UserRole.FARMER: "Farmer",
    UserRole.VETERINARY_DOCTOR: "Aquaculture Doctor",
    UserRole.SELLER: "Marketplace Seller",
    UserRole.ENTHUSIAST: "Enthusiast",
    UserRole.INDIVIDUAL: "Individual",
    UserRole.OTHER: "Other",
    UserRole.TECHNICIAN: "Technician",
    UserRole.HARDWARE_INSTALLER: "Hardware Installer",
    UserRole.ADMINISTRATOR: "Administrator",
}

PUBLIC_REGISTRATION_ROLES = {
    UserRole.FARMER,
    UserRole.VETERINARY_DOCTOR,
    UserRole.SELLER,
    UserRole.ENTHUSIAST,
    UserRole.INDIVIDUAL,
    UserRole.OTHER,
}


def group_name_for_role(role: str) -> str:
    return ROLE_GROUP_NAMES.get(role, "Other")


def assign_primary_role_group(user) -> Group:
    group, _ = Group.objects.get_or_create(name=group_name_for_role(user.primary_role))
    user.groups.add(group)
    return group
