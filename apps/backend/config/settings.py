import os
import sys
from datetime import timedelta
from pathlib import Path

from config.env import (
    get_database_config,
    get_env_bool,
    get_env_int,
    get_env_list,
    load_env_file,
)

BASE_DIR = Path(__file__).resolve().parent.parent
load_env_file(BASE_DIR / ".env")
MEDIA_ROOT = BASE_DIR / "media"
MEDIA_URL = "/media/"

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "dev-only-change-me-fittrack-ai-local-secret-key-32-plus-chars",
)
DEBUG = get_env_bool("DJANGO_DEBUG", default=True)

ALLOWED_HOSTS = get_env_list(
    "DJANGO_ALLOWED_HOSTS",
    default=["localhost", "127.0.0.1"],
)
CORS_ALLOWED_ORIGINS = get_env_list(
    "DJANGO_CORS_ALLOWED_ORIGINS",
    default=get_env_list(
        "CORS_ALLOWED_ORIGINS",
        default=["http://localhost:5173", "http://127.0.0.1:5173"],
    ),
)
CORS_ALLOW_CREDENTIALS = get_env_bool(
    "DJANGO_CORS_ALLOW_CREDENTIALS",
    default=get_env_bool("CORS_ALLOW_CREDENTIALS", default=False),
)

ROOT_URLCONF = "config.urls"

INSTALLED_APPS = [
    "accounts",
    "profiles",
    "exercises",
    "routines",
    "workouts",
    "nutrition",
    "analytics",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    "health",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "config.middleware.CorsMiddleware",
    "config.middleware.RequestIDMiddleware",
    "django.middleware.common.CommonMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [],
        },
    }
]

DATABASE_URL = (
    os.environ.get("TEST_DATABASE_URL")
    if "pytest" in sys.modules
    else os.environ.get("DATABASE_URL")
)

DATABASES = {
    "default": get_database_config(
        DATABASE_URL,
        sqlite_path=BASE_DIR / "local.sqlite3",
    )
}

AUTH_USER_MODEL = "accounts.User"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LANGUAGE_CODE = "ru"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "auth": os.environ.get("DRF_AUTH_THROTTLE_RATE", "30/min"),
        "ai_photo_upload": os.environ.get(
            "DRF_AI_PHOTO_UPLOAD_THROTTLE_RATE",
            "10/min",
        ),
    },
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "config.exceptions.api_exception_handler",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "FitTrack AI API",
    "DESCRIPTION": "Backend API for FitTrack AI mobile application.",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": False,
}

NUTRITION_AI_PHOTO_MAX_BYTES = get_env_int(
    "NUTRITION_AI_PHOTO_MAX_BYTES",
    5 * 1024 * 1024,
)
NUTRITION_AI_PHOTO_ALLOWED_CONTENT_TYPES = get_env_list(
    "NUTRITION_AI_PHOTO_ALLOWED_CONTENT_TYPES",
    default=["image/jpeg", "image/png", "image/webp"],
)
NUTRITION_AI_PHOTO_PROVIDER = os.environ.get(
    "NUTRITION_AI_PHOTO_PROVIDER",
    "disabled",
)
NUTRITION_AI_PHOTO_HTTP_ENDPOINT = os.environ.get(
    "NUTRITION_AI_PHOTO_HTTP_ENDPOINT",
    "",
)
NUTRITION_AI_PHOTO_HTTP_API_KEY = os.environ.get(
    "NUTRITION_AI_PHOTO_HTTP_API_KEY",
    "",
)
NUTRITION_AI_PHOTO_HTTP_TIMEOUT_SECONDS = get_env_int(
    "NUTRITION_AI_PHOTO_HTTP_TIMEOUT_SECONDS",
    20,
)

OPEN_FOOD_FACTS_BASE_URL = os.environ.get(
    "OPEN_FOOD_FACTS_BASE_URL",
    "https://world.openfoodfacts.org",
)
OPEN_FOOD_FACTS_TIMEOUT_SECONDS = get_env_int(
    "OPEN_FOOD_FACTS_TIMEOUT_SECONDS",
    10,
)
OPEN_FOOD_FACTS_USER_AGENT = os.environ.get(
    "OPEN_FOOD_FACTS_USER_AGENT",
    "FitTrackAI/0.1 (dev@example.com)",
)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "plain": {
            "format": "%(levelname)s %(name)s %(message)s request_id=%(request_id)s method=%(method)s path=%(path)s status_code=%(status_code)s duration_ms=%(duration_ms)s",
        },
        "standard": {
            "format": "%(levelname)s %(name)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
        "request_console": {
            "class": "logging.StreamHandler",
            "formatter": "plain",
        },
    },
    "loggers": {
        "fittrack.requests": {
            "handlers": ["request_console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "django": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
        },
    },
}
