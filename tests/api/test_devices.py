from __future__ import annotations

import pytest

from apps.devices.models import Actuator, Device, Sensor
from apps.farms.models import Farm


@pytest.mark.django_db
def test_create_device_and_registry(auth_client, farm):
    device_response = auth_client.post(
        "/api/v1/devices/",
        {
            "farmId": str(farm.id),
            "deviceId": "esp32-aquasafe-001",
            "name": "Pond Controller",
            "kind": "controller",
            "hardwareModel": "ESP32 DevKit",
        },
        format="json",
    )

    assert device_response.status_code == 201
    device_body = device_response.json()
    assert device_body["farmId"] == str(farm.id)
    assert device_body["deviceId"] == "esp32-aquasafe-001"
    device = Device.objects.get(id=device_body["id"])

    sensor_response = auth_client.post(
        "/api/v1/sensors/",
        {
            "deviceId": str(device.id),
            "key": "dissolved_oxygen",
            "name": "Dissolved Oxygen",
            "sensorType": "dissolved_oxygen",
            "unit": "mg/L",
        },
        format="json",
    )
    assert sensor_response.status_code == 201
    assert sensor_response.json()["deviceId"] == str(device.id)
    assert Sensor.objects.filter(device=device, key="dissolved_oxygen").exists()

    actuator_response = auth_client.post(
        "/api/v1/actuators/",
        {
            "deviceId": str(device.id),
            "key": "aerator",
            "name": "Aerator",
            "actuatorType": "aerator",
        },
        format="json",
    )
    assert actuator_response.status_code == 201
    assert Actuator.objects.filter(device=device, key="aerator").exists()


@pytest.mark.django_db
def test_device_requires_access_to_farm(auth_client, other_user):
    hidden = Farm.objects.create(owner=other_user, name="Hidden")

    response = auth_client.post(
        "/api/v1/devices/",
        {"farmId": str(hidden.id), "deviceId": "esp32-hidden", "name": "Hidden Device"},
        format="json",
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_device_list_is_scoped_and_filterable(auth_client, farm, other_user):
    Device.objects.create(farm=farm, device_id="esp32-a", name="A")
    Farm.objects.create(owner=other_user, name="Hidden")

    response = auth_client.get(f"/api/v1/devices/?farmId={farm.id}")

    assert response.status_code == 200
    assert [item["deviceId"] for item in response.json()["data"]] == ["esp32-a"]


@pytest.mark.django_db
def test_sensor_requires_access_to_device_farm(auth_client, other_user):
    hidden_farm = Farm.objects.create(owner=other_user, name="Hidden")
    hidden_device = Device.objects.create(farm=hidden_farm, device_id="esp32-hidden", name="Hidden")

    response = auth_client.post(
        "/api/v1/sensors/",
        {"deviceId": str(hidden_device.id), "key": "temp", "name": "Temperature"},
        format="json",
    )

    assert response.status_code == 403
