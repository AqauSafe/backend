from __future__ import annotations

import pytest

from apps.simulations.models import Simulation, SimulationRun
from apps.simulations.services import (
    WARNING_OXYGEN,
    WARNING_PH,
    WARNING_TEMPERATURE,
    normalise_legacy_reading,
)
from apps.telemetry.models import SensorReading


def run_payload(pond, **overrides):
    payload = {
        "pondId": str(pond.id),
        "durationDays": 90,
        "startingWeightG": 20,
        "dailyGrowthG": 2.5,
        "dailyFeedKg": 3,
        "dailyMortalityPercent": 1,
        "temperatureC": 28,
        "dissolvedOxygenMgL": 6,
        "ph": 7.2,
    }
    payload.update(overrides)
    return payload


@pytest.mark.django_db
def test_simulation_run_matches_frontend_contract(auth_client, farm, pond):
    response = auth_client.post("/api/v1/simulations/", run_payload(pond), format="json")

    assert response.status_code == 201
    body = response.json()
    assert body["pondId"] == str(pond.id)
    assert body["durationDays"] == 90
    assert body["startingWeightG"] == 20.0
    assert body["projectedSurvivors"] == 405
    assert body["projectedBiomassKg"] == 99.23
    assert body["totalFeedKg"] == 270.0
    assert body["estimatedFcr"] == 3.41
    assert body["warnings"] == []
    assert body["createdAt"]
    assert len(body["dailyProjection"]) == 90
    assert isinstance(body["projectedBiomassKg"], float)
    assert SimulationRun.objects.filter(pond=pond, population=pond.population).count() == 1


@pytest.mark.django_db
def test_simulation_warnings_match_frontend_text(auth_client, pond):
    response = auth_client.post(
        "/api/v1/simulations/",
        run_payload(pond, temperatureC=32, dissolvedOxygenMgL=4, ph=8.8),
        format="json",
    )

    assert response.status_code == 201
    assert response.json()["warnings"] == [WARNING_TEMPERATURE, WARNING_OXYGEN, WARNING_PH]


@pytest.mark.django_db
def test_simulation_compatibility_alias(auth_client, pond):
    response = auth_client.post("/api/simulations", run_payload(pond), format="json")

    assert response.status_code == 201
    assert response.json()["pondId"] == str(pond.id)


@pytest.mark.django_db
def test_simulation_history_is_scoped_and_filterable(auth_client, other_user, farm, pond):
    other_pond = pond.__class__.objects.create(farm=farm, name="Pond B", population=500)
    auth_client.post("/api/v1/simulations/", run_payload(pond), format="json")
    second = auth_client.post("/api/v1/simulations/", run_payload(other_pond), format="json")

    filtered = auth_client.get(f"/api/v1/simulations/?pondId={other_pond.id}")
    assert filtered.status_code == 200
    assert filtered.json()["meta"]["count"] == 1
    assert filtered.json()["data"][0]["id"] == second.json()["id"]

    from rest_framework.test import APIClient
    from rest_framework_simplejwt.tokens import RefreshToken

    api_client = APIClient()
    token = RefreshToken.for_user(other_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    forbidden = api_client.post("/api/v1/simulations/", run_payload(pond), format="json")
    assert forbidden.status_code == 403
    assert api_client.get("/api/v1/simulations/").json()["meta"]["count"] == 0


@pytest.mark.django_db
def test_simulation_state_ingestion_uses_source_simulation(auth_client, farm, pond):
    response = auth_client.post(
        "/api/v1/simulations/state/",
        {
            "pondId": str(pond.id),
            "temperature": 27.4,
            "oxygen": 5.8,
            "ph": 7.1,
            "level": 78,
            "turbidityNtu": 21.5,
            "recordedAt": "2026-11-11T10:00:00Z",
            "clientId": "sim-state-1",
        },
        format="json",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["reading"]["source"] == "simulation"
    assert body["simulation"]["pondId"] == str(pond.id)
    reading = SensorReading.objects.get(id=body["reading"]["id"])
    assert reading.source == "simulation"
    assert float(reading.oxygen) == 5.8
    assert float(reading.turbidity_ntu) == 21.5
    simulation = Simulation.objects.get(pond=pond, farm=farm)
    assert simulation.state["oxygen"] == 5.8
    assert simulation.state["turbidityNtu"] == 21.5
    assert simulation.last_state_at is not None

    latest = auth_client.get(f"/api/v1/simulations/state/?pondId={pond.id}")
    assert latest.status_code == 200
    assert latest.json()["data"]["state"]["temperature"] == 27.4


def test_legacy_reading_normalisation_prefers_named_values():
    values, raw = normalise_legacy_reading(
        {"t": 512, "p": 400, "o": 300, "l": 700, "do": 6.2, "ph": 7.4, "lvl": 81}
    )

    assert values["oxygen"] == 6.2
    assert values["ph"] == 7.4
    assert values["level"] == 81.0
    assert round(values["turbidity_ntu"], 2) == 50.05
    assert round(raw["turbidityNtu"], 2) == 50.05


def test_legacy_reading_normalisation_converts_raw_adc():
    values, raw = normalise_legacy_reading({"t": 511.5, "p": 731, "o": 426, "l": 818})

    assert round(values["oxygen"], 2) == 5.0
    assert round(values["ph"], 2) == 10.0
    assert round(values["level"], 1) == 80.0
    assert round(values["turbidity_ntu"], 2) == 50.0
    assert round(raw["turbidityNtu"], 2) == 50.0
