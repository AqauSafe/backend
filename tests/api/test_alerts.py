from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.alerts.models import Alert, AlertRule
from apps.telemetry.models import SensorReading


def make_rule(auth_client, farm, **overrides):
    payload = {
        "farmId": str(farm.id),
        "metric": "oxygen",
        "operator": "lt",
        "threshold": "5.00",
        "severity": "critical",
        "cooldownMinutes": 15,
    }
    payload.update(overrides)
    return auth_client.post("/api/v1/alert-rules/", payload, format="json")


def make_reading(auth_client, pond, oxygen, client_id):
    return auth_client.post(
        "/api/v1/readings/",
        {
            "pondId": str(pond.id),
            "source": "physical",
            "oxygen": str(oxygen),
            "recordedAt": "2026-11-11T09:00:00Z",
            "clientId": client_id,
        },
        format="json",
    )


@pytest.mark.django_db
def test_alert_rule_generates_one_active_alert(auth_client, farm, pond):
    rule_response = make_rule(auth_client, farm)
    assert rule_response.status_code == 201

    first = make_reading(auth_client, pond, "4.2", "reading-low-1")
    second = make_reading(auth_client, pond, "4.0", "reading-low-2")

    assert first.status_code == 201
    assert second.status_code == 201
    assert Alert.objects.filter(farm=farm, status=Alert.Status.ACTIVE).count() == 1
    alert = Alert.objects.get(farm=farm, status=Alert.Status.ACTIVE)
    assert alert.rule_id == AlertRule.objects.get(farm=farm).id
    assert alert.value == 4


@pytest.mark.django_db
def test_reading_above_threshold_does_not_alert(auth_client, farm, pond):
    make_rule(auth_client, farm)

    response = make_reading(auth_client, pond, "6.5", "reading-ok")

    assert response.status_code == 201
    assert Alert.objects.count() == 0


@pytest.mark.django_db
def test_alert_acknowledge_and_resolve(auth_client, farm, pond):
    make_rule(auth_client, farm)
    make_reading(auth_client, pond, "4.0", "reading-alert")
    alert = Alert.objects.get(farm=farm)

    acknowledged = auth_client.post(f"/api/v1/alerts/{alert.id}/acknowledge/", {}, format="json")
    assert acknowledged.status_code == 200
    assert acknowledged.json()["data"]["status"] == "acknowledged"

    resolved = auth_client.post(f"/api/v1/alerts/{alert.id}/resolve/", {}, format="json")
    assert resolved.status_code == 200
    assert resolved.json()["data"]["status"] == "resolved"


@pytest.mark.django_db
def test_alert_cooldown_prevents_immediate_duplicate(auth_client, farm, pond):
    make_rule(auth_client, farm)
    make_reading(auth_client, pond, "4.0", "reading-cooldown-1")
    alert = Alert.objects.get(farm=farm, status=Alert.Status.ACTIVE)
    auth_client.post(f"/api/v1/alerts/{alert.id}/resolve/", {}, format="json")

    make_reading(auth_client, pond, "3.9", "reading-cooldown-2")
    assert Alert.objects.filter(farm=farm).count() == 1

    alert.refresh_from_db()
    alert.resolved_at = timezone.now() - timedelta(minutes=30)
    alert.save(update_fields=["resolved_at"])

    make_reading(auth_client, pond, "3.8", "reading-cooldown-3")
    assert Alert.objects.filter(farm=farm).count() == 2


@pytest.mark.django_db
def test_alerts_are_scoped_to_farm_membership(auth_client, other_user, farm, pond):
    make_rule(auth_client, farm)
    make_reading(auth_client, pond, "4.0", "reading-scope")
    alert = Alert.objects.get(farm=farm)

    from rest_framework.test import APIClient
    from rest_framework_simplejwt.tokens import RefreshToken

    api_client = APIClient()
    token = RefreshToken.for_user(other_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")

    assert api_client.get(f"/api/v1/alerts/{alert.id}/").status_code == 404
    assert api_client.get("/api/v1/alerts/").json()["meta"]["count"] == 0


@pytest.mark.django_db
def test_only_managers_can_create_alert_rules(auth_client, other_user, farm):
    from apps.farms.models import FarmMembership

    FarmMembership.objects.create(farm=farm, user=other_user, role=FarmMembership.Role.WORKER)
    from rest_framework.test import APIClient
    from rest_framework_simplejwt.tokens import RefreshToken

    worker_client = APIClient()
    token = RefreshToken.for_user(other_user)
    worker_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")

    response = make_rule(worker_client, farm)

    assert response.status_code == 403
    assert SensorReading.objects.count() == 0
