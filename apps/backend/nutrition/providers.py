import json
from socket import timeout as SocketTimeout
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import base64

from django.conf import settings

from nutrition.recognitions import RECOGNITION_INVALID_FORMAT_MARKER, RECOGNITION_TIMEOUT_MARKER


class DisabledFoodPhotoRecognitionProvider:
    def recognize(self, *, image_key: str, image_file, request_payload: dict | None = None):
        return None


class RequestPayloadFoodPhotoRecognitionProvider:
    def recognize(self, *, image_key: str, image_file, request_payload: dict | None = None):
        return request_payload


class HttpJsonFoodPhotoRecognitionProvider:
    def recognize(self, *, image_key: str, image_file, request_payload: dict | None = None):
        endpoint = settings.NUTRITION_AI_PHOTO_HTTP_ENDPOINT
        if not endpoint:
            return None

        payload = {
            "image_key": image_key,
            "content_type": image_file.content_type,
        }
        if request_payload:
            payload["context"] = request_payload

        request = Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers=_build_headers(),
            method="POST",
        )

        try:
            with urlopen(
                request,
                timeout=settings.NUTRITION_AI_PHOTO_HTTP_TIMEOUT_SECONDS,
            ) as response:
                response_body = response.read().decode("utf-8")
        except (SocketTimeout, TimeoutError):
            return RECOGNITION_TIMEOUT_MARKER
        except (HTTPError, URLError):
            return None

        try:
            return json.loads(response_body)
        except json.JSONDecodeError:
            return RECOGNITION_INVALID_FORMAT_MARKER


def get_food_photo_recognition_provider():
    provider_name = settings.NUTRITION_AI_PHOTO_PROVIDER

    if provider_name == "disabled":
        return DisabledFoodPhotoRecognitionProvider()

    if provider_name == "request_payload":
        return RequestPayloadFoodPhotoRecognitionProvider()

    if provider_name == "http_json":
        return HttpJsonFoodPhotoRecognitionProvider()
    
    if provider_name == "gemini":
        return GeminiFoodPhotoRecognitionProvider()

    raise ValueError(f"Unknown nutrition AI photo provider: {provider_name}")


def parse_request_payload(raw_value):
    if raw_value in (None, ""):
        return None

    if isinstance(raw_value, dict):
        return raw_value

    if isinstance(raw_value, str):
        return json.loads(raw_value)

    return raw_value


def _build_headers() -> dict:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    if settings.NUTRITION_AI_PHOTO_HTTP_API_KEY:
        headers["Authorization"] = (
            f"Bearer {settings.NUTRITION_AI_PHOTO_HTTP_API_KEY}"
        )

    return headers


class GeminiFoodPhotoRecognitionProvider:
    def recognize(self, *, image_key: str, image_file, request_payload: dict | None = None):
        if not settings.GEMINI_API_KEY:
            return None

        image_file.seek(0)
        image_base64 = base64.b64encode(image_file.read()).decode("utf-8")
        image_file.seek(0)

        endpoint = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{settings.GEMINI_MODEL}:generateContent"
        )

        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "inline_data": {
                                "mime_type": image_file.content_type,
                                "data": image_base64,
                            }
                        },
                        {
                            "text": (
                                "Определи еду на фото. Верни только JSON без markdown. "
                                "Формат: {\"items\":[{\"name\":\"...\","
                                "\"confidence\":0.0,\"weight_g\":100,"
                                "\"calories_per_100g\":0,\"protein_per_100g\":0,"
                                "\"fat_per_100g\":0,\"carbs_per_100g\":0}]}. "
                                "Не придумывай точность: если не уверен, confidence ниже."
                            )
                        },
                    ]
                }
            ],
            "generationConfig": {
                "response_mime_type": "application/json"
            },
        }

        request = Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": settings.GEMINI_API_KEY,
            },
            method="POST",
        )

        try:
            with urlopen(
                request,
                timeout=settings.NUTRITION_AI_PHOTO_HTTP_TIMEOUT_SECONDS,
            ) as response:
                response_body = response.read().decode("utf-8")
        except (SocketTimeout, TimeoutError):
            return RECOGNITION_TIMEOUT_MARKER
        except (HTTPError, URLError):
            return None

        try:
            gemini_response = json.loads(response_body)
            text = gemini_response["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(text)
        except (KeyError, IndexError, json.JSONDecodeError):
            return RECOGNITION_INVALID_FORMAT_MARKER