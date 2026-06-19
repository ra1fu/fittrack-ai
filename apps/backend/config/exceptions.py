from rest_framework.exceptions import (
    AuthenticationFailed,
    NotAuthenticated,
    NotFound,
    PermissionDenied,
    Throttled,
)
from rest_framework.views import exception_handler
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    request = context.get("request")
    request_id = getattr(request, "request_id", None)

    if response is None:
        return response

    if response.status_code == 400:
        response.data = {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Некоторые поля заполнены неверно",
                "fields": response.data,
                "request_id": request_id,
            }
        }
        return response

    if isinstance(exc, (InvalidToken, TokenError)):
        response.data = {
            "error": {
                "code": "INVALID_TOKEN",
                "message": "Токен недействителен или истёк",
                "fields": {},
                "request_id": request_id,
            }
        }
        return response

    if isinstance(exc, NotAuthenticated):
        response.data = {
            "error": {
                "code": "NOT_AUTHENTICATED",
                "message": "Необходимо войти в аккаунт",
                "fields": {},
                "request_id": request_id,
            }
        }
        return response

    if isinstance(exc, AuthenticationFailed):
        response.data = {
            "error": {
                "code": "AUTHENTICATION_FAILED",
                "message": "Неверный email или пароль",
                "fields": {},
                "request_id": request_id,
            }
        }
        return response

    if isinstance(exc, PermissionDenied):
        response.data = {
            "error": {
                "code": "PERMISSION_DENIED",
                "message": "Недостаточно прав для выполнения действия",
                "fields": {},
                "request_id": request_id,
            }
        }
        return response

    if isinstance(exc, NotFound):
        response.data = {
            "error": {
                "code": "NOT_FOUND",
                "message": "Объект не найден",
                "fields": {},
                "request_id": request_id,
            }
        }
        return response

    if isinstance(exc, Throttled):
        response.data = {
            "error": {
                "code": "THROTTLED",
                "message": "Слишком много запросов. Повторите попытку позже",
                "fields": {
                    "wait": exc.wait,
                },
                "request_id": request_id,
            }
        }
        return response

    response.data = {
        "error": {
            "code": "API_ERROR",
            "message": "Запрос не может быть выполнен",
            "fields": {},
            "request_id": request_id,
        }
    }
    return response
