from __future__ import annotations

import pytest

from apps.telemetry.models import SensorReading


def reading_payload(pond, **overrides):
    payload = {
        "pondId": str(pond.id),
        "source": "manual",
        "temperature": "27.5",
        "oxygen": "6.2",
        "ph": "7.1",
        "level": "85",
        "recordedAt": "2026-11-11T09:00:00Z",
        "clientId": "reading-1",
    }
    payload.update(overrides)
    return payload


@pytest.mark.django_db
def test_create_manual_reading(auth_client, pond):
    response = auth_client.post("/api/v1/readings/", reading_payload(pond), format="json")

    assert response.status_code == 201
    body = response.json()
    assert body["pondId"] == str(pond.id)
    assert body["source"] == "manual"
    assert body["temperature"] == "27.50"
    assert body["oxygen"] == "6.20"
    assert body["date"] == body["recordedAt"]
    reading = SensorReading.objects.get(id=body["id"])
    assert reading.recorded_at.isoformat().startswith("2026-11-11T09:00:00")
    assert reading.received_at is not None


@pytest.mark.django_db
def test_reading_requires_at_least_one_measurement(auth_client, pond):
    response = auth_client.post(
        "/api/v1/readings/",
        {"pondId": str(pond.id), "source": "manual"},
        format="json",
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_error"


@pytest.mark.django_db
def test_reading_duplicate_client_id_is_rejected(auth_client, pond):
    payload = reading_payload(pond)
    first = auth_client.post("/api/v1/readings/", payload, format="json")
    second = auth_client.post("/api/v1/readings/", payload, format="json")

    assert first.status_code == 201
    assert second.status_code == 400
    assert "clientId" in second.json()["error"]["details"]
    assert SensorReading.objects.filter(pond=pond).count() == 1


@pytest.mark.django_db
def test_reading_history_filters_by_source_and_time(auth_client, pond):
    for index, source in enumerate(("physical", "simulation", "manual")):
        SensorReading.objects.create(
            pond=pond,
            source=source,
            recorded_at=f"2026-11-11T0{index}:00:00Z",
            oxygen=5 + index,
        )

    response = auth_client.get(f"/api/v1/readings/?pondId={pond.id}&source=simulation")

    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["count"] == 1
    assert body["data"][0]["source"] == "simulation"


@pytest.mark.django_db
def test_latest_reading_per_pond(auth_client, farm):
    from apps.farms.models import Pond

    first = Pond.objects.create(farm=farm, name="Pond One")
    second = Pond.objects.create(farm=farm, name="Pond Two")
    SensorReading.objects.create(pond=first, oxygen=5, recorded_at="2026-11-11T08:00:00Z")
    latest = SensorReading.objects.create(pond=first, oxygen=6, recorded_at="2026-11-11T10:00:00Z")
    SensorReading.objects.create(pond=second, oxygen=7, recorded_at="2026-11-11T09:00:00Z")

    response = auth_client.get("/api/v1/readings/latest/")

    assert response.status_code == 200
    result = response.json()["data"]
    by_pond = {item["pondId"]: item for item in result}
    assert by_pond[str(first.id)]["id"] == str(latest.id)
    assert len(result) == 2


@pytest.mark.django_db
def test_cannot_add_reading_to_another_users_pond(auth_client, other_user):
    from apps.farms.models import Farm, Pond

    hidden_farm = Farm.objects.create(owner=other_user, name="Hidden")
    hidden_pond = Pond.objects.create(farm=hidden_farm, name="Hidden Pond")

    response = auth_client.post("/api/v1/readings/", reading_payload(hidden_pond), format="json")

    assert response.status_code == 403


@pytest.mark.django_db
def test_readings_are_immutable(auth_client, pond):
    reading = SensorReading.objects.create(pond=pond, oxygen=5)

    response = auth_client.patch(f"/api/v1/readings/{reading.id}/", {"oxygen": "4"}, format="json")

    assert response.status_code == 405


@pytest.mark.django_db
def test_dashboard_summary(auth_client, farm, pond):
    from apps.telemetry.models import ReadingSource

    SensorReading.objects.create(
        pond=pond, oxygen=6.1, source=ReadingSource.PHYSICAL, recorded_at="2026-11-11T09:00:00Z"
    )

    response = auth_client.get("/api/v1/dashboard/summary/")

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["farms"] == 1
    assert body["ponds"] == 1
    assert body["readings"] == 1
    assert len(body["latestReadings"]) == 1
    assert body["latestReadings"][0]["pondId"] == str(pond.id)
