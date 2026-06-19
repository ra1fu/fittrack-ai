#!/bin/sh
set -e

python - <<'PY'
import os
import socket
import time
from urllib.parse import urlparse

database_url = os.environ.get("DATABASE_URL", "")

if database_url.startswith(("postgres://", "postgresql://")):
    parsed_url = urlparse(database_url)
    host = parsed_url.hostname or "localhost"
    port = parsed_url.port or 5432
    deadline = time.time() + int(os.environ.get("DATABASE_WAIT_TIMEOUT_SECONDS", "60"))

    while True:
        try:
            with socket.create_connection((host, port), timeout=2):
                break
        except OSError:
            if time.time() >= deadline:
                raise SystemExit(f"Database is not available at {host}:{port}")
            time.sleep(1)
PY

if [ "${DJANGO_RUN_MIGRATIONS:-false}" = "true" ]; then
    python manage.py migrate --noinput
fi

if [ "${DJANGO_SEED_CATALOGS:-false}" = "true" ]; then
    python manage.py seed_exercise_catalogs
    python manage.py seed_food_catalog
fi

exec "$@"
