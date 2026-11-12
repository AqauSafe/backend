from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.commands.models import Command
from apps.commands.tasks import expire_device_commands
from apps.devices.models import Device
from apps.devices.tasks import mark_stale_devices
from apps.farms.models import FarmMembership
from integrations.mqtt.crypto import encrypt_secret
from integrations.mqtt.signing import verify_command


def make_device(farm, pond, device_id="esp32-command"):
    return Device.objects.create(
        farm=farm,
        pond=pond,
        device_id=device_id,
        name="Command Device",
        status=Device.Status.PROVISIONED,
        secret_encrypted=encrypt_secret("broker-password"),
        command_secret_encrypted=encrypt_secret("device-secret"),
        provisioned_at=timezone.now(),
    )


@pytest.mark.django_db
def test_create_signed_command(auth_client, farm, pond, monkeypatch):
    device = make_device(farm, pond)
    published = []

    def fake_publish(topic, payload, **kwargs):
        published.append((topic, payload, kwargs))

    monkeypatch.setattr("apps.commands.services.publish_message", fake_publish)

    response = auth_client.post(
        "/api/v1/commands/",
        {
            "deviceId": str(device.id),
            "commandType": "aerator.set",
            "payload": {"on": True},
            "ttlSeconds": 30,
        },
        format="json",
    )

    assert response.status_code == 201
    body = response.json()["data"]
    assert body["status"] == "sent"
    assert body["commandType"] == "aerator.set"
    assert len(body["signature"]) == 64
    assert body["sentAt"]
    assert published[0][0] == f"aquasafe/v1/devices/{device.device_id}/commands"
    assert published[0][1]["type"] == "aerator.set"
    assert published[0][1]["payload"] == {"on": True}
    assert published[0][1]["signature"] == body["signature"]
    command = Command.objects.get(id=body["id"])
    assert verify_command("device-secret", command, body["signature"])
    assert not verify_command("broker-password", command, body["signature"])


@pytest.mark.django_db
def test_command_requires_provisioned_device(auth_client, farm, pond):
    device = Device.objects.create(
        farm=farm, pond=pond, device_id="esp32-unprovisioned", name="Unprovisioned"
    )

    response = auth_client.post(
        "/api/v1/commands/",
        {"deviceId": str(device.id), "commandType": "aerator.set"},
        format="json",
    )

    assert response.status_code == 400
    assert Command.objects.count() == 0


@pytest.mark.django_db
def test_worker_cannot_command_device(other_client, other_user, farm, pond, monkeypatch):
    FarmMembership.objects.create(farm=farm, user=other_user, role=FarmMembership.Role.WORKER)
    device = make_device(farm, pond)
    monkeypatch.setattr("apps.commands.services.publish_message", lambda *a, **k: None)

    response = other_client.post(
        "/api/v1/commands/",
        {"deviceId": str(device.id), "commandType": "aerator.set"},
        format="json",
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_expire_commands_task(farm, pond):
    device = make_device(farm, pond)
    command = Command.objects.create(
        device=device,
        command_type="aerator.set",
        expires_at=timezone.now() - timedelta(minutes=1),
        status=Command.Status.SENT,
    )

    assert expire_device_commands() == 1
    command.refresh_from_db()
    assert command.status == Command.Status.EXPIRED


@pytest.mark.django_db
def test_mark_stale_devices_task(farm, pond):
    device = make_device(farm, pond)
    device.status = Device.Status.ONLINE
    device.last_seen_at = timezone.now() - timedelta(minutes=10)
    device.save(update_fields=["status", "last_seen_at"])

    assert mark_stale_devices() == 1
    device.refresh_from_db()
    assert device.status == Device.Status.OFFLINE
