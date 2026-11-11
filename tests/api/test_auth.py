from __future__ import annotations

import pytest
from django.core.management import call_command

from apps.accounts.models import User


def register_payload(**overrides):
    payload = {
        "name": "Ada Farmer",
        "email": "ada@example.com",
        "password": "strong-password-123",
        "phone": "+2348000000000",
        "role": "Fish Farmer",
        "language": "en",
    }
    payload.update(overrides)
    return payload


@pytest.mark.django_db
def test_register_returns_user_and_tokens(api_client):
    response = api_client.post("/api/v1/auth/register/", register_payload(), format="json")

    assert response.status_code == 201
    body = response.json()["data"]
    assert body["user"]["email"] == "ada@example.com"
    assert body["user"]["role"] == "Fish Farmer"
    assert body["user"]["otherRole"] == ""
    assert body["user"]["roles"] == ["Farmer"]
    assert body["access"]
    assert body["refresh"]
    assert User.objects.filter(email="ada@example.com").exists()


@pytest.mark.django_db
def test_register_rejects_duplicate_email(api_client):
    User.objects.create_user(
        email="ada@example.com", password="strong-password-123", name="Existing"
    )

    response = api_client.post("/api/v1/auth/register/", register_payload(), format="json")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_error"
    assert "email" in response.json()["error"]["details"]


@pytest.mark.django_db
def test_register_rejects_weak_password(api_client):
    response = api_client.post(
        "/api/v1/auth/register/", register_payload(password="123"), format="json"
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_error"


@pytest.mark.django_db
def test_register_requires_other_role_when_other_selected(api_client):
    response = api_client.post(
        "/api/v1/auth/register/", register_payload(role="Other"), format="json"
    )

    assert response.status_code == 400
    assert "otherRole" in response.json()["error"]["details"]


@pytest.mark.django_db
def test_login_returns_tokens(api_client, user):
    response = api_client.post(
        "/api/v1/auth/login/",
        {"email": "FARMER@example.com", "password": "strong-password-123"},
        format="json",
    )

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["user"]["email"] == "farmer@example.com"
    assert body["access"]
    assert body["refresh"]


@pytest.mark.django_db
def test_login_rejects_bad_password(api_client, user):
    response = api_client.post(
        "/api/v1/auth/login/",
        {"email": "farmer@example.com", "password": "wrong-password"},
        format="json",
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_failed"


@pytest.mark.django_db
def test_me_requires_authentication(api_client):
    response = api_client.get("/api/v1/users/me/")
    assert response.status_code == 401


@pytest.mark.django_db
def test_me_returns_current_user(auth_client, user):
    response = auth_client.get("/api/v1/users/me/")

    assert response.status_code == 200
    assert response.json()["email"] == user.email
    assert response.json()["role"] == "Fish Farmer"


@pytest.mark.django_db
def test_me_update(auth_client):
    response = auth_client.patch(
        "/api/v1/users/me/",
        {"name": "Updated Farmer", "phone": "+2348111111111", "language": "ha"},
        format="json",
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Updated Farmer"
    assert response.json()["phone"] == "+2348111111111"


@pytest.mark.django_db
def test_refresh_rotates_token(api_client):
    register = api_client.post("/api/v1/auth/register/", register_payload(), format="json")
    refresh = register.json()["data"]["refresh"]

    response = api_client.post("/api/v1/auth/refresh/", {"refresh": refresh}, format="json")

    assert response.status_code == 200
    assert response.json()["data"]["access"]
    assert response.json()["data"]["refresh"] != refresh


@pytest.mark.django_db
def test_logout_blacklists_refresh_token(api_client):
    register = api_client.post("/api/v1/auth/register/", register_payload(), format="json")
    refresh = register.json()["data"]["refresh"]

    logout = api_client.post("/api/v1/auth/logout/", {"refresh": refresh}, format="json")
    assert logout.status_code == 204

    response = api_client.post("/api/v1/auth/refresh/", {"refresh": refresh}, format="json")
    assert response.status_code == 401


@pytest.mark.django_db
def test_change_password(auth_client, user):
    response = auth_client.post(
        "/api/v1/auth/change-password/",
        {"oldPassword": "strong-password-123", "newPassword": "new-strong-password-456"},
        format="json",
    )

    assert response.status_code == 204
    user.refresh_from_db()
    assert user.check_password("new-strong-password-456")


@pytest.mark.django_db
def test_change_password_rejects_wrong_old_password(auth_client):
    response = auth_client.post(
        "/api/v1/auth/change-password/",
        {"oldPassword": "wrong-password", "newPassword": "new-strong-password-456"},
        format="json",
    )

    assert response.status_code == 400
    assert "oldPassword" in response.json()["error"]["details"]


@pytest.mark.django_db
def test_roles_are_admin_only(api_client, auth_client):
    forbidden = auth_client.get("/api/v1/roles/")
    assert forbidden.status_code == 403

    call_command("seed_roles")
    admin = User.objects.create_user(
        email="root@example.com",
        password="strong-password-123",
        name="Root",
        primary_role="Administrator",
        is_staff=True,
    )
    from rest_framework_simplejwt.tokens import RefreshToken

    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(admin).access_token}")
    response = api_client.get("/api/v1/roles/")
    assert response.status_code == 200
    assert len(response.json()) >= 1
    names = {role["name"] for role in response.json()}
    assert "Farmer" in names
    assert "Administrator" in names
