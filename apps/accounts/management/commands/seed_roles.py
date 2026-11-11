"""Seed configurable AquaSafe role groups and their permissions."""

from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

from apps.accounts.roles import ROLE_GROUP_NAMES

ROLE_PERMISSIONS: dict[str, list[str]] = {
    "Farmer": [
        "farms.add_farm",
        "farms.change_farm",
        "farms.delete_farm",
        "farms.view_farm",
        "farms.add_pond",
        "farms.change_pond",
        "farms.delete_pond",
        "farms.view_pond",
        "farms.add_feeding",
        "farms.view_feeding",
        "devices.view_device",
        "devices.add_device",
        "devices.change_device",
        "telemetry.view_sensorreading",
        "telemetry.add_sensorreading",
        "alerts.view_alert",
        "alerts.change_alert",
        "simulations.add_simulation",
        "simulations.view_simulation",
        "marketplace.add_product",
        "marketplace.view_product",
        "messaging.view_conversation",
        "messaging.add_message",
        "support.add_supportticket",
        "support.view_supportticket",
        "installations.add_servicerequest",
        "installations.view_servicerequest",
        "subscriptions.view_subscription",
    ],
    "Aquaculture Doctor": [
        "farms.view_farm",
        "farms.view_pond",
        "telemetry.view_sensorreading",
        "alerts.view_alert",
        "farms.view_feeding",
        "support.view_supportticket",
        "support.change_supportticket",
    ],
    "Marketplace Seller": [
        "marketplace.add_product",
        "marketplace.change_product",
        "marketplace.delete_product",
        "marketplace.view_product",
        "marketplace.view_order",
        "marketplace.change_order",
    ],
    "Enthusiast": [
        "farms.view_farm",
        "marketplace.view_product",
        "messaging.view_conversation",
    ],
    "Individual": [
        "marketplace.view_product",
        "messaging.view_conversation",
    ],
    "Other": [
        "marketplace.view_product",
        "messaging.view_conversation",
    ],
    "Technician": [
        "devices.view_device",
        "devices.change_device",
        "telemetry.view_sensorreading",
        "installations.view_servicerequest",
        "installations.change_servicerequest",
    ],
    "Hardware Installer": [
        "devices.view_device",
        "installations.view_servicerequest",
        "installations.change_servicerequest",
    ],
    "Administrator": [],
}

ALL_PERMISSION_GROUP = "Administrator"


def permission_queryset(specs: list[str]):
    query = None
    for spec in specs:
        app_label, codename = spec.split(".", 1)
        current = Permission.objects.filter(content_type__app_label=app_label, codename=codename)
        query = current if query is None else query | current
    return Permission.objects.none() if query is None else query


class Command(BaseCommand):
    help = "Create or update AquaSafe role groups and assign permissions."

    def handle(self, *args, **options):
        created = []
        updated = []

        for _role, group_name in ROLE_GROUP_NAMES.items():
            group, was_created = Group.objects.get_or_create(name=group_name)
            (created if was_created else updated).append(group_name)
            if group_name == ALL_PERMISSION_GROUP:
                permissions = Permission.objects.all()
            else:
                permissions = permission_queryset(ROLE_PERMISSIONS.get(group_name, []))
            group.permissions.set(permissions)
            self.stdout.write(
                f"{'Created' if was_created else 'Updated'} role '{group_name}' "
                f"with {permissions.count()} permission(s)."
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Role seeding complete. Created {len(created)}, updated {len(updated)}."
            )
        )
