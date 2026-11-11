import pytest


@pytest.mark.django_db
def test_health_is_public(api_client):
    response = api_client.get("/health/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.django_db
def test_readiness_checks_database(api_client):
    response = api_client.get("/ready/")
    assert response.status_code == 200
    assert response.json()["checks"]["database"] == "ok"


def test_api_docs_render(api_client):
    response = api_client.get("/api/docs/")
    assert response.status_code == 200


def test_openapi_schema_is_available(api_client):
    response = api_client.get("/api/schema/", HTTP_ACCEPT="application/yaml")
    assert response.status_code == 200
    assert b"openapi:" in response.content
