from pathlib import Path

import pytest

from config.env import get_database_config
from rest_framework import status
from rest_framework.test import APIClient


def test_get_database_config_returns_sqlite_when_database_url_is_empty():
    config = get_database_config("", sqlite_path=Path("/tmp/local.sqlite3"))

    assert config == {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": Path("/tmp/local.sqlite3"),
    }


def test_get_database_config_parses_postgres_database_url():
    config = get_database_config(
        "postgres://fittrack:secret@localhost:5433/fittrack_db",
        sqlite_path=Path("/tmp/local.sqlite3"),
    )

    assert config == {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "fittrack_db",
        "USER": "fittrack",
        "PASSWORD": "secret",
        "HOST": "localhost",
        "PORT": "5433",
    }


def test_get_database_config_parses_postgres_sslmode():
    config = get_database_config(
        "postgresql://fittrack:secret@db/fittrack_db?sslmode=require",
        sqlite_path=Path("/tmp/local.sqlite3"),
    )

    assert config["OPTIONS"] == {
        "sslmode": "require",
    }


def test_get_database_config_rejects_unsupported_scheme():
    with pytest.raises(ValueError):
        get_database_config(
            "mysql://fittrack:secret@localhost/fittrack_db",
            sqlite_path=Path("/tmp/local.sqlite3"),
        )


def test_pytest_uses_sqlite_when_test_database_url_is_not_set(settings):
    assert settings.DATABASES["default"]["ENGINE"] == "django.db.backends.sqlite3"


def test_request_id_middleware_adds_response_header():
    client = APIClient()

    response = client.get(
        "/api/v1/health/",
        HTTP_X_REQUEST_ID="test-request-id",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response["X-Request-ID"] == "test-request-id"


def test_exception_response_contains_request_id():
    client = APIClient()

    response = client.get(
        "/api/v1/me",
        HTTP_X_REQUEST_ID="test-error-request-id",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["error"]["request_id"] == "test-error-request-id"
    assert response["X-Request-ID"] == "test-error-request-id"


def test_cors_preflight_allows_configured_frontend_origin(settings):
    settings.CORS_ALLOWED_ORIGINS = ["http://localhost:5173"]
    client = APIClient()

    response = client.options(
        "/api/v1/auth/login",
        HTTP_ORIGIN="http://localhost:5173",
        HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
        HTTP_ACCESS_CONTROL_REQUEST_HEADERS="authorization,content-type",
    )

    assert response.status_code == 204
    assert response["Access-Control-Allow-Origin"] == "http://localhost:5173"
    assert "POST" in response["Access-Control-Allow-Methods"]
    assert "Authorization" in response["Access-Control-Allow-Headers"]


def test_cors_headers_are_not_added_for_unconfigured_origin(settings):
    settings.CORS_ALLOWED_ORIGINS = ["http://localhost:5173"]
    client = APIClient()

    response = client.get(
        "/api/v1/health/",
        HTTP_ORIGIN="http://evil.example",
    )

    assert response.status_code == status.HTTP_200_OK
    assert "Access-Control-Allow-Origin" not in response


def test_openapi_schema_is_available():
    client = APIClient()

    response = client.get("/api/v1/schema/")
    schema = response.content.decode()

    assert response.status_code == status.HTTP_200_OK
    assert "/api/v1/auth/login" in schema
    assert "auth_login" in schema
    assert "dashboard_summary" in schema


def test_openapi_auth_endpoints_include_request_and_response_bodies():
    client = APIClient()

    response = client.get("/api/v1/schema/")
    schema = response.content.decode()

    assert response.status_code == status.HTTP_200_OK
    assert "$ref: '#/components/schemas/Login'" in schema
    assert "$ref: '#/components/schemas/LoginResponse'" in schema
    assert "$ref: '#/components/schemas/Register'" in schema
    assert "$ref: '#/components/schemas/RegisterResponse'" in schema
