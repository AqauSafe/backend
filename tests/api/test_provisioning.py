from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.devices.models import Device
from apps.farms.models import FarmMembership


@pytest.mark.django_db
def test_provision_and_claim_device(auth_client, farm, pond):
    device = Device.objects.create(
        farm=farm,
        pond=pond,
        device_id="esp32-claim-1",
        name="Claimable Device",
    )

    provision = auth_client.post(f"/api/v1/devices/{device.id}/provision/")
    assert provision.status_code == 200
    provision_body = provision.json()["data"]
    token = provision_body["claimToken"]
    assert provision_body["topics"]["telemetry"].endswith("esp32-claim-1/telemetry")
    assert "secretEncrypted" not in provision_body
    assert "claimTokenHash" not in provision_body

    claim = auth_client.post(
        "/api/v1/devices/claim/",
        {"deviceId": "esp32-claim-1", "claimToken": token},
        format="json",
    )
    assert claim.status_code == 200
    claim_body = claim.json()["data"]
    assert claim_body["mqttUsername"] == "esp32-claim-1"
    assert claim_body["mqttPassword"]
    assert claim_body["commandSecret"]
    assert claim_body["mqttPassword"] != claim_body["commandSecret"]
    assert claim_body["topics"]["commands"].endswith("esp32-claim-1/commands")

    device.refresh_from_db()
    assert device.provisioned_at is not None
    assert device.claim_token_hash == ""
    assert device.secret_encrypted
    assert device.command_secret_encrypted
    assert device.secret_encrypted != device.command_secret_encrypted
    assert device.status == Device.Status.PROVISIONED

    replay = auth_client.post(
        "/api/v1/devices/claim/",
        {"deviceId": "esp32-claim-1", "claimToken": token},
        format="json",
    )
    assert replay.status_code == 400


@pytest.mark.django_db
def test_claim_rejects_wrong_or_expired_token(auth_client, farm):
    device = Device.objects.create(farm=farm, device_id="esp32-claim-2", name="Claimable Device")
    token = auth_client.post(f"/api/v1/devices/{device.id}/provision/").json()["data"]["claimToken"]

    wrong = auth_client.post(
        "/api/v1/devices/claim/",
        {"deviceId": "esp32-claim-2", "claimToken": token + "x"},
        format="json",
    )
    assert wrong.status_code == 400

    device.claim_expires_at = timezone.now() - timedelta(minutes=1)
    device.save(update_fields=["claim_expires_at"])
    expired = auth_client.post(
        "/api/v1/devices/claim/",
        {"deviceId": "esp32-claim-2", "claimToken": token},
        format="json",
    )
    assert expired.status_code == 400


@pytest.mark.django_db
def test_worker_cannot_provision_device(other_client, other_user, farm):
    FarmMembership.objects.create(farm=farm, user=other_user, role=FarmMembership.Role.WORKER)
    device = Device.objects.create(farm=farm, device_id="esp32-worker", name="Worker Device")

    response = other_client.post(f"/api/v1/devices/{device.id}/provision/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_publish_device_config(auth_client, farm, pond, monkeypatch):
    device = Device.objects.create(
        farm=farm,
        pond=pond,
        device_id="esp32-config-1",
        name="Configurable Device",
    )
    published = []

    def fake_publish(topic, payload, **kwargs):
        published.append((topic, payload, kwargs))

    monkeypatch.setattr("apps.devices.views.publish_message", fake_publish)

    response = auth_client.post(
        f"/api/v1/devices/{device.id}/config/",
        {"config": {"sampleIntervalSeconds": 30, "automation": True}},
        format="json",
    )

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["version"] == 2
    assert body["config"]["sampleIntervalSeconds"] == 30
    assert published[0][0] == "aquasafe/v1/devices/esp32-config-1/config"
    assert published[0][1]["version"] == 2
    assert published[0][1]["config"] == {"sampleIntervalSeconds": 30, "automation": True}

    device.refresh_from_db()
    assert device.config_version == 2
    assert device.config == {"sample_interval_seconds": 30, "automation": True}
