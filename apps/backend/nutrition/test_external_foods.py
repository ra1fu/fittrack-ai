from socket import timeout as SocketTimeout

import pytest
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User
from nutrition.models import Food, FoodSource


class FakeResponse:
    def __init__(self, body: bytes):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return self.body


def authenticate_client(user):
    access = str(RefreshToken.for_user(user).access_token)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return client


@pytest.mark.django_db
@override_settings(
    OPEN_FOOD_FACTS_BASE_URL="https://world.openfoodfacts.test",
    OPEN_FOOD_FACTS_USER_AGENT="FitTrackAI/0.1 (test@example.com)",
)
def test_lookup_food_by_barcode_creates_external_food(monkeypatch):
    calls = {}

    def fake_urlopen(request, timeout):
        calls["url"] = request.full_url
        calls["user_agent"] = request.headers["User-agent"]
        return FakeResponse(
            b'{"status":"success","product":{"product_name":"Protein Bar",'
            b'"brands":"Test Brand","nutriments":{"energy-kcal_100g":390,'
            b'"proteins_100g":32,"fat_100g":12,"carbohydrates_100g":40,'
            b'"fiber_100g":8}}}'
        )

    monkeypatch.setattr("nutrition.external_foods.urlopen", fake_urlopen)
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    client = authenticate_client(user)

    response = client.get("/api/v1/foods/barcodes/12345678/lookup")

    body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert body["data"]["name"] == "Protein Bar"
    assert body["data"]["brand"] == "Test Brand"
    assert body["data"]["barcode"] == "12345678"
    assert body["data"]["source"] == FoodSource.EXTERNAL
    assert body["data"]["is_verified"] is False
    assert calls["url"] == "https://world.openfoodfacts.test/api/v3.6/product/12345678.json"
    assert calls["user_agent"] == "FitTrackAI/0.1 (test@example.com)"

    food = Food.objects.get(barcode="12345678")

    assert food.owner is None
    assert food.external_id == "openfoodfacts:12345678"


@pytest.mark.django_db
def test_lookup_food_by_barcode_uses_local_cache(monkeypatch):
    def fake_urlopen(request, timeout):
        raise AssertionError("External API should not be called")

    monkeypatch.setattr("nutrition.external_foods.urlopen", fake_urlopen)
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    food = Food.objects.create(
        name="Cached Product",
        barcode="12345678",
        source=FoodSource.EXTERNAL,
        external_id="openfoodfacts:12345678",
        calories_per_100g="100.00",
        protein_per_100g="10.00",
        fat_per_100g="2.00",
        carbs_per_100g="12.00",
    )
    client = authenticate_client(user)

    response = client.get("/api/v1/foods/barcodes/12345678/lookup")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["data"]["id"] == str(food.id)


@pytest.mark.django_db
def test_lookup_food_by_barcode_rejects_invalid_barcode():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    client = authenticate_client(user)

    response = client.get("/api/v1/foods/barcodes/not-a-code/lookup")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "barcode" in response.json()["error"]["fields"]


@pytest.mark.django_db
def test_lookup_food_by_barcode_returns_404_for_external_not_found(monkeypatch):
    def fake_urlopen(request, timeout):
        return FakeResponse(b'{"status":"product_not_found"}')

    monkeypatch.setattr("nutrition.external_foods.urlopen", fake_urlopen)
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    client = authenticate_client(user)

    response = client.get("/api/v1/foods/barcodes/12345678/lookup")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.django_db
def test_lookup_food_by_barcode_handles_external_timeout(monkeypatch):
    def fake_urlopen(request, timeout):
        raise SocketTimeout()

    monkeypatch.setattr("nutrition.external_foods.urlopen", fake_urlopen)
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    client = authenticate_client(user)

    response = client.get("/api/v1/foods/barcodes/12345678/lookup")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "barcode" in response.json()["error"]["fields"]


@pytest.mark.django_db
def test_lookup_food_by_barcode_rejects_external_product_without_nutrients(monkeypatch):
    def fake_urlopen(request, timeout):
        return FakeResponse(
            b'{"status":"success","product":{"product_name":"Mystery Product"}}'
        )

    monkeypatch.setattr("nutrition.external_foods.urlopen", fake_urlopen)
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    client = authenticate_client(user)

    response = client.get("/api/v1/foods/barcodes/12345678/lookup")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "barcode" in response.json()["error"]["fields"]
