import os
from pathlib import Path
from urllib.parse import parse_qs, urlparse

def get_env_bool(name: str, default: bool = False) -> bool:
    raw_value = os.environ.get(name)

    if raw_value is None:
        return default

    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def get_env_list(name: str, default: list[str] | None = None) -> list[str]:
    raw_value = os.environ.get(name)

    if raw_value is None:
        return default or []

    return [item.strip() for item in raw_value.split(",") if item.strip()]


def get_env_int(name: str, default: int) -> int:
    raw_value = os.environ.get(name)

    if raw_value is None:
        return default

    return int(raw_value)


def get_database_config(database_url: str | None, *, sqlite_path: Path) -> dict:
    if not database_url:
        return {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": sqlite_path,
        }

    parsed_url = urlparse(database_url)

    if parsed_url.scheme not in {"postgres", "postgresql"}:
        raise ValueError("DATABASE_URL supports only postgres/postgresql URLs")

    query = parse_qs(parsed_url.query)
    config = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": parsed_url.path.lstrip("/"),
        "USER": parsed_url.username or "",
        "PASSWORD": parsed_url.password or "",
        "HOST": parsed_url.hostname or "localhost",
        "PORT": str(parsed_url.port or 5432),
    }

    if "sslmode" in query:
        config["OPTIONS"] = {
            "sslmode": query["sslmode"][0],
        }

    return config


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
