from socket import timeout as SocketTimeout
from urllib.error import URLError

import pytest
from django.test import override_settings

from nutrition.providers import GeminiFoodPhotoRecognitionProvider, HttpJsonFoodPhotoRecognitionProvider
from nutrition.recognitions import (
    RECOGNITION_INVALID_FORMAT_MARKER,
    RECOGNITION_PROVIDER_CONFIG_ERROR_MARKER,
    RECOGNITION_PROVIDER_HTTP_ERROR_MARKER,
    RECOGNITION_TIMEOUT_MARKER,
)


class FakeImageFile:
    content_type = "image/jpeg"

    def seek(self, position):
        self.position = position

    def read(self):
        return b"fake-image"


class FakeResponse:
    def __init__(self, body: bytes):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return self.body


@override_settings(
    NUTRITION_AI_PHOTO_HTTP_ENDPOINT="https://ai.example.test/recognize",
    NUTRITION_AI_PHOTO_HTTP_API_KEY="test-key",
    NUTRITION_AI_PHOTO_HTTP_TIMEOUT_SECONDS=7,
)
def test_http_json_provider_returns_decoded_ai_response(monkeypatch):
    calls = {}

    def fake_urlopen(request, timeout):
        calls["request"] = request
        calls["timeout"] = timeout
        return FakeResponse(
            b'{"items":[{"name":"Rice","confidence":0.8,'
            b'"weight_g":100,"calories_per_100g":130,'
            b'"protein_per_100g":2.7,"fat_per_100g":0.3,'
            b'"carbs_per_100g":28}]}'
        )

    monkeypatch.setattr("nutrition.providers.urlopen", fake_urlopen)

    response = HttpJsonFoodPhotoRecognitionProvider().recognize(
        image_key="nutrition/photo-recognitions/user/photo.jpg",
        image_file=FakeImageFile(),
    )

    assert response["items"][0]["name"] == "Rice"
    assert calls["timeout"] == 7
    assert calls["request"].headers["Authorization"] == "Bearer test-key"


@override_settings(
    NUTRITION_AI_PHOTO_HTTP_ENDPOINT="https://ai.example.test/recognize",
    NUTRITION_AI_PHOTO_HTTP_API_KEY="",
    NUTRITION_AI_PHOTO_HTTP_TIMEOUT_SECONDS=7,
)
def test_http_json_provider_returns_timeout_marker_on_timeout(monkeypatch):
    def fake_urlopen(request, timeout):
        raise SocketTimeout()

    monkeypatch.setattr("nutrition.providers.urlopen", fake_urlopen)

    response = HttpJsonFoodPhotoRecognitionProvider().recognize(
        image_key="nutrition/photo-recognitions/user/photo.jpg",
        image_file=FakeImageFile(),
    )

    assert response == RECOGNITION_TIMEOUT_MARKER


@override_settings(
    NUTRITION_AI_PHOTO_HTTP_ENDPOINT="https://ai.example.test/recognize",
    NUTRITION_AI_PHOTO_HTTP_API_KEY="",
    NUTRITION_AI_PHOTO_HTTP_TIMEOUT_SECONDS=7,
)
def test_http_json_provider_returns_invalid_format_marker_for_broken_json(monkeypatch):
    def fake_urlopen(request, timeout):
        return FakeResponse(b"not-json")

    monkeypatch.setattr("nutrition.providers.urlopen", fake_urlopen)

    response = HttpJsonFoodPhotoRecognitionProvider().recognize(
        image_key="nutrition/photo-recognitions/user/photo.jpg",
        image_file=FakeImageFile(),
    )

    assert response == RECOGNITION_INVALID_FORMAT_MARKER


@override_settings(
    NUTRITION_AI_PHOTO_HTTP_ENDPOINT="",
    NUTRITION_AI_PHOTO_HTTP_API_KEY="",
)
def test_http_json_provider_returns_none_without_endpoint():
    response = HttpJsonFoodPhotoRecognitionProvider().recognize(
        image_key="nutrition/photo-recognitions/user/photo.jpg",
        image_file=FakeImageFile(),
    )

    assert response == RECOGNITION_PROVIDER_CONFIG_ERROR_MARKER


@override_settings(GEMINI_API_KEY="")
def test_gemini_provider_returns_config_error_without_api_key():
    response = GeminiFoodPhotoRecognitionProvider().recognize(
        image_key="nutrition/photo-recognitions/user/photo.jpg",
        image_file=FakeImageFile(),
    )

    assert response == RECOGNITION_PROVIDER_CONFIG_ERROR_MARKER


@override_settings(
    GEMINI_API_KEY="test-key",
    GEMINI_MODEL="gemini-3.5-flash",
    NUTRITION_AI_PHOTO_HTTP_TIMEOUT_SECONDS=7,
)
def test_gemini_provider_returns_http_error_marker(monkeypatch):
    def fake_urlopen(request, timeout):
        raise URLError("boom")

    monkeypatch.setattr("nutrition.providers.urlopen", fake_urlopen)

    response = GeminiFoodPhotoRecognitionProvider().recognize(
        image_key="nutrition/photo-recognitions/user/photo.jpg",
        image_file=FakeImageFile(),
    )

    assert response == RECOGNITION_PROVIDER_HTTP_ERROR_MARKER
