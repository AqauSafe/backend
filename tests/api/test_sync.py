from __future__ import annotations

from decimal import Decimal

import pytest

from apps.farms.models import Farm, Feeding, Pond
from apps.telemetry.models import SensorReading


def app_data_payload():
    return {
        "farms": [{"id": "farm-local-1", "name": "Green Valley", "location": "Lagos"}],
        "ponds": [
            {
                "id": "pond-local-1",
                "farmId": "farm-local-1",
                "name": "Pond A",
                "population": 1200,
                "length": 10,
                "width": 5,
                "status": "active",
            }
        ],
        "feedings": [
            {
                "id": "feeding-local-1",
                "pondId": "pond-local-1",
                "amount": 2.5,
                "date": "2026-11-11T08:00:00Z",
            }
        ],
        "readings": [
            {
                "id": "reading-local-1",
                "pondId": "pond-local-1",
                "temperature": 27.5,
                "oxygen": 6.1,
                "ph": 7.2,
                "level": 80,
                "date": "2026-11-11T09:00:00Z",
            }
        ],
        "listings": [{"id": "listing-1", "name": "Feed"}],
        "messages": [{"id": "message-1", "text": "Hello"}],
    }


@pytest.mark.django_db
def test_import_frontend_app_data(auth_client, user):
    response = auth_client.post("/api/v1/sync/import/", app_data_payload(), format="json")

    assert response.status_code == 200
    summary = response.json()["data"]
    assert summary["farms"]["created"] == 1
    assert summary["ponds"]["created"] == 1
    assert summary["feedings"]["created"] == 1
    assert summary["readings"]["created"] == 1
    assert summary["ignored"] == {"listings": 1, "messages": 1}
    assert summary["errors"] == []

    farm = Farm.objects.get(owner=user, client_id="farm-local-1")
    pond = Pond.objects.get(farm=farm, client_id="pond-local-1")
    assert pond.name == "Pond A"
    assert Feeding.objects.filter(pond=pond, client_id="feeding-local-1").exists()
    reading = SensorReading.objects.get(pond=pond, client_id="reading-local-1")
    assert reading.source == "import"
    assert reading.oxygen == Decimal("6.1")


@pytest.mark.django_db
def test_import_is_idempotent(auth_client, user):
    payload = app_data_payload()
    first = auth_client.post("/api/v1/sync/import/", payload, format="json")
    second = auth_client.post("/api/v1/sync/import/", payload, format="json")

    assert first.status_code == 200
    assert second.status_code == 200
    summary = second.json()["data"]
    assert summary["farms"]["created"] == 0
    assert summary["ponds"]["created"] == 0
    assert summary["feedings"]["created"] == 0
    assert summary["readings"]["created"] == 0
    assert Farm.objects.filter(owner=user).count() == 1
    assert Pond.objects.count() == 1
    assert Feeding.objects.count() == 1
    assert SensorReading.objects.count() == 1


@pytest.mark.django_db
def test_import_reports_records_with_missing_farm(auth_client):
    payload = {"ponds": [{"id": "orphan-pond", "farmId": "missing-farm", "name": "Orphan"}]}

    response = auth_client.post("/api/v1/sync/import/", payload, format="json")

    assert response.status_code == 200
    summary = response.json()["data"]
    assert summary["ponds"]["created"] == 0
    assert len(summary["errors"]) == 1
    assert summary["errors"][0]["section"] == "ponds"


@pytest.mark.django_db
def test_bootstrap_returns_only_accessible_data(auth_client, farm, pond, other_user):
    Farm.objects.create(owner=other_user, name="Hidden Farm")
    Feeding.objects.create(pond=pond, amount=1)
    SensorReading.objects.create(pond=pond, oxygen=6)

    response = auth_client.get("/api/v1/sync/bootstrap/")

    assert response.status_code == 200
    body = response.json()["data"]
    assert [item["name"] for item in body["farms"]] == ["Green Valley"]
    assert [item["name"] for item in body["ponds"]] == ["Pond A"]
    assert len(body["feedings"]) == 1
    assert len(body["readings"]) == 1
    assert body["listings"] == []
    assert body["messages"] == []
