from __future__ import annotations

import pytest

from apps.farms.models import Farm, FarmMembership, Feeding, Pond


@pytest.mark.django_db
def test_farms_require_authentication(api_client):
    response = api_client.get("/api/v1/farms/")
    assert response.status_code == 401


@pytest.mark.django_db
def test_create_farm_sets_owner_and_membership(auth_client, user):
    response = auth_client.post(
        "/api/v1/farms/",
        {"name": "Green Valley", "location": "Lagos", "clientId": "farm-local-1"},
        format="json",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Green Valley"
    assert body["clientId"] == "farm-local-1"
    assert body["ownerId"] == str(user.id)
    farm = Farm.objects.get(id=body["id"])
    assert farm.owner == user
    membership = FarmMembership.objects.get(farm=farm, user=user)
    assert membership.role == FarmMembership.Role.OWNER


@pytest.mark.django_db
def test_farm_list_excludes_other_users_farms(auth_client, farm, other_user):
    Farm.objects.create(owner=other_user, name="Hidden Farm", location="Abuja")

    response = auth_client.get("/api/v1/farms/")

    assert response.status_code == 200
    body = response.json()
    assert [item["name"] for item in body["data"]] == ["Green Valley"]
    assert body["meta"]["count"] == 1


@pytest.mark.django_db
def test_farm_retrieve_is_scoped_to_membership(auth_client, other_user):
    hidden = Farm.objects.create(owner=other_user, name="Hidden Farm")

    response = auth_client.get(f"/api/v1/farms/{hidden.id}/")

    assert response.status_code == 404


@pytest.mark.django_db
def test_owner_can_update_farm(auth_client, farm):
    response = auth_client.patch(f"/api/v1/farms/{farm.id}/", {"location": "Ibadan"}, format="json")

    assert response.status_code == 200
    farm.refresh_from_db()
    assert farm.location == "Ibadan"


@pytest.mark.django_db
def test_create_pond_in_owned_farm(auth_client, farm):
    response = auth_client.post(
        "/api/v1/ponds/",
        {
            "farmId": str(farm.id),
            "name": "Pond B",
            "population": 2500,
            "length": "12.5",
            "width": "8",
            "species": "Catfish",
        },
        format="json",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["farmId"] == str(farm.id)
    assert body["name"] == "Pond B"
    assert body["area"] == "100.00"
    assert Pond.objects.filter(farm=farm, name="Pond B").exists()


@pytest.mark.django_db
def test_cannot_create_pond_in_another_users_farm(auth_client, other_user):
    hidden = Farm.objects.create(owner=other_user, name="Hidden Farm")

    response = auth_client.post(
        "/api/v1/ponds/",
        {"farmId": str(hidden.id), "name": "Intrusion", "population": 10},
        format="json",
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_farm_manager_can_add_pond(other_client, farm, other_user):
    FarmMembership.objects.create(farm=farm, user=other_user, role=FarmMembership.Role.MANAGER)

    response = other_client.post(
        "/api/v1/ponds/",
        {"farmId": str(farm.id), "name": "Manager Pond"},
        format="json",
    )

    assert response.status_code == 201


@pytest.mark.django_db
def test_pond_list_filters_by_farm(auth_client, farm, pond):
    other_farm = Farm.objects.create(owner=farm.owner, name="Second Farm")
    Pond.objects.create(farm=other_farm, name="Other Pond")

    response = auth_client.get(f"/api/v1/ponds/?farmId={farm.id}")

    assert response.status_code == 200
    assert [item["name"] for item in response.json()["data"]] == ["Pond A"]


@pytest.mark.django_db
def test_record_feeding(auth_client, pond, user):
    response = auth_client.post(
        "/api/v1/feedings/",
        {
            "pondId": str(pond.id),
            "amount": "2.5",
            "fedAt": "2026-11-11T08:30:00Z",
            "clientId": "feeding-1",
            "note": "Morning feeding",
        },
        format="json",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["amount"] == "2.500"
    assert body["clientId"] == "feeding-1"
    assert body["createdById"] == str(user.id)
    assert Feeding.objects.filter(pond=pond, client_id="feeding-1").exists()


@pytest.mark.django_db
def test_duplicate_feeding_client_id_is_rejected(auth_client, pond):
    payload = {"pondId": str(pond.id), "amount": "1", "clientId": "feeding-dup"}
    first = auth_client.post("/api/v1/feedings/", payload, format="json")
    second = auth_client.post("/api/v1/feedings/", payload, format="json")

    assert first.status_code == 201
    assert second.status_code == 400
    assert "clientId" in second.json()["error"]["details"]
