import json
from decimal import Decimal, InvalidOperation
from socket import timeout as SocketTimeout
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from django.conf import settings

from nutrition.models import Food, FoodDataQuality, FoodSource


def lookup_food_by_barcode(*, barcode: str) -> Food:
    normalized_barcode = normalize_barcode(barcode)
    existing_food = Food.objects.filter(
        owner__isnull=True,
        barcode=normalized_barcode,
        is_active=True,
    ).order_by("source", "name").first()

    if existing_food is not None:
        return existing_food

    payload = fetch_open_food_facts_product(normalized_barcode)
    mapped_food = map_open_food_facts_product(payload, normalized_barcode)

    food, _ = Food.objects.update_or_create(
        owner=None,
        source=FoodSource.EXTERNAL,
        external_id=f"openfoodfacts:{normalized_barcode}",
        defaults={
            **mapped_food,
            "barcode": normalized_barcode,
            "data_quality": FoodDataQuality.MEDIUM,
            "is_verified": False,
            "is_active": True,
        },
    )

    return food


def fetch_open_food_facts_product(barcode: str) -> dict:
    base_url = settings.OPEN_FOOD_FACTS_BASE_URL.rstrip("/")
    url = f"{base_url}/api/v3.6/product/{quote(barcode)}.json"
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": settings.OPEN_FOOD_FACTS_USER_AGENT,
        },
        method="GET",
    )

    try:
        with urlopen(request, timeout=settings.OPEN_FOOD_FACTS_TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))
    except (SocketTimeout, TimeoutError) as exc:
        raise ExternalFoodLookupTimeout("Open Food Facts timed out") from exc
    except HTTPError as exc:
        if exc.code == 404:
            raise ExternalFoodNotFound("Продукт не найден во внешнем каталоге") from exc
        raise ExternalFoodLookupError("Open Food Facts request failed") from exc
    except (URLError, json.JSONDecodeError) as exc:
        raise ExternalFoodLookupError("Open Food Facts response is unavailable") from exc


def map_open_food_facts_product(payload: dict, barcode: str) -> dict:
    if payload.get("status") in {"failure", "product_not_found"}:
        raise ExternalFoodNotFound("Продукт не найден во внешнем каталоге")

    product = payload.get("product")
    if not isinstance(product, dict):
        raise ExternalFoodNotFound("Продукт не найден во внешнем каталоге")

    nutriments = product.get("nutriments")
    if not isinstance(nutriments, dict):
        raise ExternalFoodInvalidData("Во внешнем каталоге нет БЖУ для продукта")

    name = (
        product.get("product_name")
        or product.get("product_name_en")
        or product.get("generic_name")
        or f"Product {barcode}"
    )

    return {
        "name": str(name).strip()[:200],
        "brand": str(product.get("brands") or "").strip()[:160],
        "serving_size": None,
        "serving_unit": "",
        "calories_per_100g": _get_required_decimal(
            nutriments,
            "energy-kcal_100g",
        ),
        "protein_per_100g": _get_required_decimal(nutriments, "proteins_100g"),
        "fat_per_100g": _get_required_decimal(nutriments, "fat_100g"),
        "carbs_per_100g": _get_required_decimal(nutriments, "carbohydrates_100g"),
        "fiber_per_100g": _get_optional_decimal(nutriments, "fiber_100g"),
    }


def normalize_barcode(barcode: str) -> str:
    normalized = barcode.strip()

    if not normalized.isdigit():
        raise ExternalFoodInvalidBarcode("Штрихкод должен содержать только цифры")

    if len(normalized) < 8 or len(normalized) > 14:
        raise ExternalFoodInvalidBarcode("Штрихкод должен содержать от 8 до 14 цифр")

    return normalized


def _get_required_decimal(payload: dict, key: str) -> Decimal:
    value = _get_optional_decimal(payload, key)

    if value is None:
        raise ExternalFoodInvalidData("Во внешнем каталоге нет полного БЖУ продукта")

    return value


def _get_optional_decimal(payload: dict, key: str) -> Decimal | None:
    value = payload.get(key)

    if value in (None, ""):
        return None

    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ExternalFoodInvalidData("Во внешнем каталоге некорректные данные БЖУ") from exc

    if decimal_value < 0:
        raise ExternalFoodInvalidData("Во внешнем каталоге некорректные данные БЖУ")

    return decimal_value


class ExternalFoodLookupError(Exception):
    pass


class ExternalFoodLookupTimeout(ExternalFoodLookupError):
    pass


class ExternalFoodNotFound(ExternalFoodLookupError):
    pass


class ExternalFoodInvalidBarcode(ExternalFoodLookupError):
    pass


class ExternalFoodInvalidData(ExternalFoodLookupError):
    pass
