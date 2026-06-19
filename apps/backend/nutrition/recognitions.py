from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

from nutrition.calculations import calculate_nutrients_from_per_100g
from nutrition.models import (
    FoodRecognition,
    FoodRecognitionErrorCode,
    FoodRecognitionItem,
    FoodRecognitionStatus,
    Meal,
    MealItem,
    MealItemSource,
)


RECOGNITION_TIMEOUT_MARKER = "timeout"
RECOGNITION_INVALID_FORMAT_MARKER = "invalid_format"
RECOGNITION_PROVIDER_DISABLED_MARKER = "provider_disabled"
RECOGNITION_PROVIDER_CONFIG_ERROR_MARKER = "provider_config_error"
RECOGNITION_PROVIDER_HTTP_ERROR_MARKER = "provider_http_error"


def create_food_recognition_from_ai_response(*, user, image_key: str, raw_ai_response):
    recognition = FoodRecognition.objects.create(
        user=user,
        image_key=image_key,
        raw_ai_response=raw_ai_response,
        status=FoodRecognitionStatus.DRAFT,
    )

    try:
        parsed_items = parse_ai_food_response(raw_ai_response)
    except FoodRecognitionParseError as exc:
        recognition.status = FoodRecognitionStatus.FAILED
        recognition.error_code = exc.code
        recognition.error_message = exc.message
        recognition.save(
            update_fields=[
                "status",
                "error_code",
                "error_message",
                "updated_at",
            ]
        )
        return recognition

    FoodRecognitionItem.objects.bulk_create(
        [
            FoodRecognitionItem(
                recognition=recognition,
                position=index,
                ai_name=item["name"],
                ai_confidence=item["confidence"],
                ai_weight_g=item["weight_g"],
                ai_calories_per_100g=item["calories_per_100g"],
                ai_protein_per_100g=item["protein_per_100g"],
                ai_fat_per_100g=item["fat_per_100g"],
                ai_carbs_per_100g=item["carbs_per_100g"],
                corrected_name=item["name"],
                corrected_weight_g=item["weight_g"],
                corrected_calories_per_100g=item["calories_per_100g"],
                corrected_protein_per_100g=item["protein_per_100g"],
                corrected_fat_per_100g=item["fat_per_100g"],
                corrected_carbs_per_100g=item["carbs_per_100g"],
            )
            for index, item in enumerate(parsed_items)
        ]
    )

    return recognition


def parse_ai_food_response(raw_ai_response) -> list[dict]:
    if raw_ai_response is None:
        raise FoodRecognitionParseError(
            FoodRecognitionErrorCode.NO_RESPONSE,
            "AI не вернул ответ",
        )

    if raw_ai_response == RECOGNITION_PROVIDER_DISABLED_MARKER:
        raise FoodRecognitionParseError(
            FoodRecognitionErrorCode.NO_RESPONSE,
            "AI-распознавание отключено на backend",
        )

    if raw_ai_response == RECOGNITION_PROVIDER_CONFIG_ERROR_MARKER:
        raise FoodRecognitionParseError(
            FoodRecognitionErrorCode.NO_RESPONSE,
            "AI-распознавание не настроено: проверьте provider, API key и endpoint",
        )

    if raw_ai_response == RECOGNITION_PROVIDER_HTTP_ERROR_MARKER:
        raise FoodRecognitionParseError(
            FoodRecognitionErrorCode.NO_RESPONSE,
            "AI API не ответил успешно: проверьте API key, модель и доступность сервиса",
        )

    if raw_ai_response == RECOGNITION_TIMEOUT_MARKER:
        raise FoodRecognitionParseError(
            FoodRecognitionErrorCode.TIMEOUT,
            "Истекло время ожидания AI-ответа",
        )

    if raw_ai_response == RECOGNITION_INVALID_FORMAT_MARKER:
        raise FoodRecognitionParseError(
            FoodRecognitionErrorCode.INVALID_FORMAT,
            "AI вернул некорректный формат ответа",
        )

    if not isinstance(raw_ai_response, dict):
        raise FoodRecognitionParseError(
            FoodRecognitionErrorCode.INVALID_FORMAT,
            "AI-ответ должен быть JSON-объектом",
        )

    items = raw_ai_response.get("items")
    if not isinstance(items, list) or len(items) == 0:
        raise FoodRecognitionParseError(
            FoodRecognitionErrorCode.INVALID_FORMAT,
            "AI-ответ должен содержать непустой список items",
        )

    return [_parse_ai_food_item(item) for item in items]


def update_recognition_item_from_corrections(item, validated_data: dict):
    for field, value in validated_data.items():
        setattr(item, field, value)

    item.user_corrected = True
    item.save(update_fields=[*validated_data.keys(), "user_corrected", "updated_at"])

    return item


@transaction.atomic
def confirm_food_recognition(*, recognition, meal_data: dict):
    if recognition.status != FoodRecognitionStatus.DRAFT:
        raise FoodRecognitionConfirmError("Распознавание уже обработано")

    items = list(recognition.items.order_by("position", "created_at"))
    if not items:
        raise FoodRecognitionConfirmError("В распознавании нет позиций для сохранения")

    meal_id = meal_data.get("meal_id")
    if meal_id:
        try:
            meal = Meal.objects.get(id=meal_id, user=recognition.user)
        except Meal.DoesNotExist as exc:
            raise FoodRecognitionConfirmError("Приём пищи не найден") from exc
    else:
        meal = Meal.objects.create(
            user=recognition.user,
            meal_date=meal_data["meal_date"],
            meal_type=meal_data["meal_type"],
            custom_name=meal_data.get("custom_name", ""),
            eaten_at=meal_data.get("eaten_at"),
            notes=meal_data.get("notes", ""),
        )

    for recognition_item in items:
        nutrients = calculate_nutrients_from_per_100g(
            calories_per_100g=recognition_item.corrected_calories_per_100g,
            protein_per_100g=recognition_item.corrected_protein_per_100g,
            fat_per_100g=recognition_item.corrected_fat_per_100g,
            carbs_per_100g=recognition_item.corrected_carbs_per_100g,
            weight_g=recognition_item.corrected_weight_g,
        )
        MealItem.objects.create(
            meal=meal,
            food=None,
            display_name_snapshot=recognition_item.corrected_name,
            weight_g=recognition_item.corrected_weight_g,
            calories_snapshot=nutrients["calories"],
            protein_snapshot=nutrients["protein"],
            fat_snapshot=nutrients["fat"],
            carbs_snapshot=nutrients["carbs"],
            source=MealItemSource.AI,
            ai_recognition_item_id=recognition_item.id,
        )

    recognition.status = FoodRecognitionStatus.CONFIRMED
    recognition.confirmed_meal = meal
    recognition.confirmed_at = timezone.now()
    recognition.save(
        update_fields=[
            "status",
            "confirmed_meal",
            "confirmed_at",
            "updated_at",
        ]
    )

    return meal


def _parse_ai_food_item(item) -> dict:
    if not isinstance(item, dict):
        raise FoodRecognitionParseError(
            FoodRecognitionErrorCode.INVALID_FORMAT,
            "Каждый item должен быть JSON-объектом",
        )

    name = item.get("name")
    if not isinstance(name, str) or not name.strip():
        raise FoodRecognitionParseError(
            FoodRecognitionErrorCode.INVALID_FORMAT,
            "У каждого item должно быть название",
        )

    parsed_item = {
        "name": name.strip(),
        "confidence": _parse_decimal(item.get("confidence"), "confidence"),
        "weight_g": _parse_decimal(item.get("weight_g"), "weight_g"),
        "calories_per_100g": _parse_decimal(
            item.get("calories_per_100g"),
            "calories_per_100g",
        ),
        "protein_per_100g": _parse_decimal(
            item.get("protein_per_100g"),
            "protein_per_100g",
        ),
        "fat_per_100g": _parse_decimal(item.get("fat_per_100g"), "fat_per_100g"),
        "carbs_per_100g": _parse_decimal(item.get("carbs_per_100g"), "carbs_per_100g"),
    }

    if parsed_item["confidence"] < 0 or parsed_item["confidence"] > 1:
        raise FoodRecognitionParseError(
            FoodRecognitionErrorCode.INVALID_FORMAT,
            "confidence должен быть от 0 до 1",
        )

    if parsed_item["weight_g"] <= 0:
        raise FoodRecognitionParseError(
            FoodRecognitionErrorCode.INVALID_FORMAT,
            "weight_g должен быть больше 0",
        )

    for field in (
        "calories_per_100g",
        "protein_per_100g",
        "fat_per_100g",
        "carbs_per_100g",
    ):
        if parsed_item[field] < 0:
            raise FoodRecognitionParseError(
                FoodRecognitionErrorCode.INVALID_FORMAT,
                f"{field} не может быть отрицательным",
            )

    return parsed_item


def _parse_decimal(value, field_name: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise FoodRecognitionParseError(
            FoodRecognitionErrorCode.INVALID_FORMAT,
            f"{field_name} должен быть числом",
        ) from exc


class FoodRecognitionParseError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class FoodRecognitionConfirmError(Exception):
    pass
