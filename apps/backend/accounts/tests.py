import uuid

import pytest
from django.core.cache import cache
from django.db import IntegrityError

from accounts.models import User

from rest_framework import status
from rest_framework.test import APIClient
from rest_framework.throttling import ScopedRateThrottle

from profiles.models import UserProfile


@pytest.mark.django_db
def test_create_user_normalizes_email_and_hashes_password():
    user = User.objects.create_user(
        email="USER@Example.COM",
        password="strong-password-123",
    )

    assert isinstance(user.id, uuid.UUID)
    assert user.email == "user@example.com"
    assert user.check_password("strong-password-123")
    assert user.password != "strong-password-123"
    assert user.is_active is True
    assert user.is_staff is False
    assert user.is_superuser is False
    assert user.email_verified is False


@pytest.mark.django_db
def test_create_user_requires_email():
    with pytest.raises(ValueError, match="Email is required"):
        User.objects.create_user(email="", password="strong-password-123")


@pytest.mark.django_db
def test_user_email_must_be_unique():
    User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )

    with pytest.raises(IntegrityError):
        User.objects.create_user(
            email="user@example.com",
            password="another-password-123",
        )


@pytest.mark.django_db
def test_create_superuser_sets_required_admin_flags():
    user = User.objects.create_superuser(
        email="admin@example.com",
        password="strong-password-123",
    )

    assert user.is_staff is True
    assert user.is_superuser is True
    assert user.is_active is True
    assert user.email_verified is True


@pytest.mark.django_db
def test_create_superuser_rejects_invalid_staff_flag():
    with pytest.raises(ValueError, match="Superuser must have is_staff=True"):
        User.objects.create_superuser(
            email="admin@example.com",
            password="strong-password-123",
            is_staff=False,
        )


@pytest.mark.django_db
def test_create_superuser_rejects_invalid_superuser_flag():
    with pytest.raises(ValueError, match="Superuser must have is_superuser=True"):
        User.objects.create_superuser(
            email="admin@example.com",
            password="strong-password-123",
            is_superuser=False,
        )

def test_register_user_successfully(db):
    client = APIClient()

    response = client.post(
        "/api/v1/auth/register",
        {
            "email": "USER@Example.COM",
            "password": "strong-password-123",
            "accepted_terms": True,
            "accepted_privacy": True,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["data"]["email"] == "user@example.com"
    assert response.json()["data"]["email_verified"] is False

    user = User.objects.get(email="user@example.com")

    assert user.check_password("strong-password-123")
    assert UserProfile.objects.filter(user=user).exists()


def test_register_user_rejects_duplicate_email(db):
    User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )

    client = APIClient()

    response = client.post(
        "/api/v1/auth/register",
        {
            "email": "USER@example.com",
            "password": "strong-password-123",
            "accepted_terms": True,
            "accepted_privacy": True,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "email" in response.json()["error"]["fields"]


def test_register_user_rejects_short_password(db):
    client = APIClient()

    response = client.post(
        "/api/v1/auth/register",
        {
            "email": "user@example.com",
            "password": "short",
            "accepted_terms": True,
            "accepted_privacy": True,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "password" in response.json()["error"]["fields"]


def test_register_user_requires_terms_acceptance(db):
    client = APIClient()

    response = client.post(
        "/api/v1/auth/register",
        {
            "email": "user@example.com",
            "password": "strong-password-123",
            "accepted_terms": False,
            "accepted_privacy": True,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "accepted_terms" in response.json()["error"]["fields"]


def test_register_user_requires_privacy_acceptance(db):
    client = APIClient()

    response = client.post(
        "/api/v1/auth/register",
        {
            "email": "user@example.com",
            "password": "strong-password-123",
            "accepted_terms": True,
            "accepted_privacy": False,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "accepted_privacy" in response.json()["error"]["fields"]

def test_login_user_successfully(db):
    User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )

    client = APIClient()

    response = client.post(
        "/api/v1/auth/login",
        {
            "email": "USER@example.com",
            "password": "strong-password-123",
        },
        format="json",
    )

    body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert body["data"]["access"]
    assert body["data"]["refresh"]
    assert body["data"]["user"]["email"] == "user@example.com"


def test_login_user_rejects_wrong_password(db):
    User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )

    client = APIClient()

    response = client.post(
        "/api/v1/auth/login",
        {
            "email": "user@example.com",
            "password": "wrong-password-123",
        },
        format="json",
    )

    body = response.json()

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert body["error"]["code"] == "AUTHENTICATION_FAILED"
    assert body["error"]["message"] == "Неверный email или пароль"


def test_login_user_rejects_unknown_email(db):
    client = APIClient()

    response = client.post(
        "/api/v1/auth/login",
        {
            "email": "missing@example.com",
            "password": "strong-password-123",
        },
        format="json",
    )

    body = response.json()

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert body["error"]["code"] == "AUTHENTICATION_FAILED"
    assert body["error"]["message"] == "Неверный email или пароль"


def test_login_user_rejects_inactive_user(db):
    User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
        is_active=False,
    )

    client = APIClient()

    response = client.post(
        "/api/v1/auth/login",
        {
            "email": "user@example.com",
            "password": "strong-password-123",
        },
        format="json",
    )

    body = response.json()

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert body["error"]["code"] == "AUTHENTICATION_FAILED"


def test_login_is_rate_limited(db, monkeypatch):
    cache.clear()
    monkeypatch.setitem(ScopedRateThrottle.THROTTLE_RATES, "auth", "1/min")
    User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    client = APIClient()

    first_response = client.post(
        "/api/v1/auth/login",
        {
            "email": "user@example.com",
            "password": "wrong-password-123",
        },
        format="json",
    )
    second_response = client.post(
        "/api/v1/auth/login",
        {
            "email": "user@example.com",
            "password": "wrong-password-123",
        },
        format="json",
    )

    assert first_response.status_code == status.HTTP_401_UNAUTHORIZED
    assert second_response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert second_response.json()["error"]["code"] == "THROTTLED"
    assert "wait" in second_response.json()["error"]["fields"]


def test_refresh_token_returns_new_access_and_refresh(db):
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    client = APIClient()

    login_response = client.post(
        "/api/v1/auth/login",
        {
            "email": user.email,
            "password": "strong-password-123",
        },
        format="json",
    )
    old_refresh = login_response.json()["data"]["refresh"]

    response = client.post(
        "/api/v1/auth/refresh",
        {
            "refresh": old_refresh,
        },
        format="json",
    )

    body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert body["data"]["access"]
    assert body["data"]["refresh"]
    assert body["data"]["refresh"] != old_refresh


def test_refresh_token_rejects_reused_rotated_token(db):
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    client = APIClient()

    login_response = client.post(
        "/api/v1/auth/login",
        {
            "email": user.email,
            "password": "strong-password-123",
        },
        format="json",
    )
    old_refresh = login_response.json()["data"]["refresh"]

    first_refresh_response = client.post(
        "/api/v1/auth/refresh",
        {
            "refresh": old_refresh,
        },
        format="json",
    )

    assert first_refresh_response.status_code == status.HTTP_200_OK

    second_refresh_response = client.post(
        "/api/v1/auth/refresh",
        {
            "refresh": old_refresh,
        },
        format="json",
    )

    assert second_refresh_response.status_code == status.HTTP_401_UNAUTHORIZED
    assert second_refresh_response.json()["error"]["code"] == "INVALID_TOKEN"


def test_logout_revokes_refresh_token(db):
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    client = APIClient()

    login_response = client.post(
        "/api/v1/auth/login",
        {
            "email": user.email,
            "password": "strong-password-123",
        },
        format="json",
    )
    refresh = login_response.json()["data"]["refresh"]

    logout_response = client.post(
        "/api/v1/auth/logout",
        {
            "refresh": refresh,
        },
        format="json",
    )

    assert logout_response.status_code == status.HTTP_200_OK
    assert logout_response.json()["data"]["success"] is True

    refresh_response = client.post(
        "/api/v1/auth/refresh",
        {
            "refresh": refresh,
        },
        format="json",
    )

    assert refresh_response.status_code == status.HTTP_401_UNAUTHORIZED
    assert refresh_response.json()["error"]["code"] == "INVALID_TOKEN"


def test_logout_rejects_invalid_refresh_token(db):
    client = APIClient()

    response = client.post(
        "/api/v1/auth/logout",
        {
            "refresh": "invalid-token",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "refresh" in response.json()["error"]["fields"]
