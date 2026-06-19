import logging
import time
import uuid

from django.conf import settings
from django.http import HttpResponse


logger = logging.getLogger("fittrack.requests")


class CorsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == "OPTIONS" and self._is_allowed_origin(request):
            response = HttpResponse(status=204)
        else:
            response = self.get_response(request)

        if self._is_allowed_origin(request):
            self._add_cors_headers(request, response)

        return response

    def _is_allowed_origin(self, request) -> bool:
        origin = request.headers.get("Origin")
        return bool(origin and origin in settings.CORS_ALLOWED_ORIGINS)

    def _add_cors_headers(self, request, response) -> None:
        origin = request.headers["Origin"]
        response["Access-Control-Allow-Origin"] = origin
        response["Vary"] = "Origin"
        response["Access-Control-Allow-Methods"] = "GET, POST, PATCH, DELETE, OPTIONS"
        response["Access-Control-Allow-Headers"] = (
            "Authorization, Content-Type, X-Request-ID"
        )
        response["Access-Control-Max-Age"] = "86400"

        if settings.CORS_ALLOW_CREDENTIALS:
            response["Access-Control-Allow-Credentials"] = "true"


class RequestIDMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.request_id = request_id
        started_at = time.monotonic()

        response = self.get_response(request)

        duration_ms = int((time.monotonic() - started_at) * 1000)
        response["X-Request-ID"] = request_id

        logger.info(
            "request_finished",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )

        return response
