from __future__ import annotations

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.farms.models import Farm, FarmMembership, Pond


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def user(db) -> User:
    return User.objects.create_user(
        email="farmer@example.com",
        password="strong-password-123",
        name="Test Farmer",
        primary_role="Fish Farmer",
    )


@pytest.fixture
def other_user(db) -> User:
    return User.objects.create_user(
        email="other@example.com",
        password="strong-password-123",
        name="Other Farmer",
        primary_role="Fish Farmer",
    )


@pytest.fixture
def admin_user(db) -> User:
    return User.objects.create_user(
        email="admin@example.com",
        password="strong-password-123",
        name="Test Admin",
        primary_role="Administrator",
        is_staff=True,
    )


@pytest.fixture
def farm(user) -> Farm:
    farm = Farm.objects.create(owner=user, name="Green Valley", location="Lagos")
    FarmMembership.objects.create(farm=farm, user=user, role=FarmMembership.Role.OWNER)
    return farm


@pytest.fixture
def pond(farm) -> Pond:
    return Pond.objects.create(
        farm=farm,
        name="Pond A",
        population=1000,
        length=10,
        width=5,
        depth=1.5,
        species="Catfish",
    )


@pytest.fixture
def auth_client(api_client, user) -> APIClient:
    token = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    return api_client


@pytest.fixture
def other_client(api_client, other_user) -> APIClient:
    token = RefreshToken.for_user(other_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    return api_client


@pytest.fixture
def admin_client(api_client, admin_user) -> APIClient:
    token = RefreshToken.for_user(admin_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    return api_client
