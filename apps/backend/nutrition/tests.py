import pytest
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.storage import default_storage
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User
from nutrition.models import (
    Food,
    FoodRecognition,
    FoodRecognitionErrorCode,
    FoodRecognitionItem,
    FoodRecognitionStatus,
    FoodSource,
    Meal,
    MealItem,
    MealItemSource,
    MealType,
)
from profiles.models import GoalType, UserGoal


def authenticate_client(user):
    access = str(RefreshToken.for_user(user).access_token)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return client


def build_uploaded_photo(
    *,
    name="meal.jpg",
    content=b"fake-image-content",
    content_type="image/jpeg",
):
    return SimpleUploadedFile(
        name,
        content,
        content_type=content_type,
    )


@pytest.mark.django_db
def test_create_food_successfully():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    client = authenticate_client(user)

    response = client.post(
        "/api/v1/foods",
        {
            "name": "Творог",
            "brand": "Домашний",
            "serving_size": "150.00",
            "serving_unit": "g",
            "calories_per_100g": "120.00",
            "protein_per_100g": "18.00",
            "fat_per_100g": "5.00",
            "carbs_per_100g": "3.00",
        },
        format="json",
    )

    body = response.json()

    assert response.status_code == status.HTTP_201_CREATED
    assert body["data"]["name"] == "Творог"
    assert body["data"]["owner_id"] == str(user.id)
    assert body["data"]["source"] == FoodSource.USER

    food = Food.objects.get(id=body["data"]["id"])

    assert food.owner == user


@pytest.mark.django_db
def test_create_food_requires_authentication():
    client = APIClient()

    response = client.post(
        "/api/v1/foods",
        {
            "name": "Творог",
            "calories_per_100g": "120.00",
            "protein_per_100g": "18.00",
            "fat_per_100g": "5.00",
            "carbs_per_100g": "3.00",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["error"]["code"] == "NOT_AUTHENTICATED"


@pytest.mark.django_db
def test_get_foods_returns_system_and_current_user_foods_only():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    other_user = User.objects.create_user(
        email="other@example.com",
        password="strong-password-123",
    )
    system_food = Food.objects.create(
        name="Рис",
        source=FoodSource.SYSTEM,
        calories_per_100g="130.00",
        protein_per_100g="2.70",
        fat_per_100g="0.30",
        carbs_per_100g="28.00",
    )
    user_food = Food.objects.create(
        owner=user,
        name="Мой творог",
        source=FoodSource.USER,
        calories_per_100g="120.00",
        protein_per_100g="18.00",
        fat_per_100g="5.00",
        carbs_per_100g="3.00",
    )
    Food.objects.create(
        owner=other_user,
        name="Чужой продукт",
        source=FoodSource.USER,
        calories_per_100g="100.00",
        protein_per_100g="10.00",
        fat_per_100g="1.00",
        carbs_per_100g="1.00",
    )
    client = authenticate_client(user)

    response = client.get("/api/v1/foods")

    body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert body["meta"]["count"] == 2
    assert {item["id"] for item in body["data"]} == {
        str(system_food.id),
        str(user_food.id),
    }


@pytest.mark.django_db
def test_create_meal_successfully():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    client = authenticate_client(user)

    response = client.post(
        "/api/v1/meals",
        {
            "meal_date": "2026-06-18",
            "meal_type": MealType.BREAKFAST,
            "custom_name": "",
            "notes": "После тренировки",
        },
        format="json",
    )

    body = response.json()

    assert response.status_code == status.HTTP_201_CREATED
    assert body["data"]["meal_date"] == "2026-06-18"
    assert body["data"]["meal_type"] == MealType.BREAKFAST
    assert body["data"]["items"] == []
    assert body["data"]["totals"] == {
        "calories": "0.00",
        "protein": "0.00",
        "fat": "0.00",
        "carbs": "0.00",
    }

    meal = Meal.objects.get(id=body["data"]["id"])

    assert meal.user == user


@pytest.mark.django_db
def test_create_meal_is_idempotent_by_local_device_id():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    client = authenticate_client(user)
    payload = {
        "meal_date": "2026-06-18",
        "meal_type": MealType.BREAKFAST,
        "local_device_id": "00000000-0000-0000-0000-000000000001",
        "client_updated_at": "2026-06-18T10:00:00Z",
    }

    first_response = client.post("/api/v1/meals", payload, format="json")
    second_response = client.post("/api/v1/meals", payload, format="json")

    assert first_response.status_code == status.HTTP_201_CREATED
    assert second_response.status_code == status.HTTP_201_CREATED
    assert second_response.json()["data"]["id"] == first_response.json()["data"]["id"]
    assert Meal.objects.filter(user=user).count() == 1


@pytest.mark.django_db
def test_create_meal_local_device_id_is_scoped_to_user():
    first_user = User.objects.create_user(
        email="first@example.com",
        password="strong-password-123",
    )
    second_user = User.objects.create_user(
        email="second@example.com",
        password="strong-password-123",
    )
    payload = {
        "meal_date": "2026-06-18",
        "meal_type": MealType.BREAKFAST,
        "local_device_id": "00000000-0000-0000-0000-000000000001",
    }

    first_response = authenticate_client(first_user).post(
        "/api/v1/meals",
        payload,
        format="json",
    )
    second_response = authenticate_client(second_user).post(
        "/api/v1/meals",
        payload,
        format="json",
    )

    assert first_response.status_code == status.HTTP_201_CREATED
    assert second_response.status_code == status.HTTP_201_CREATED
    assert first_response.json()["data"]["id"] != second_response.json()["data"]["id"]
    assert Meal.objects.count() == 2


@pytest.mark.django_db
def test_add_meal_item_by_weight_creates_snapshot():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    meal = Meal.objects.create(
        user=user,
        meal_date="2026-06-18",
        meal_type=MealType.BREAKFAST,
    )
    food = Food.objects.create(
        owner=user,
        name="Творог",
        source=FoodSource.USER,
        calories_per_100g="120.00",
        protein_per_100g="18.00",
        fat_per_100g="5.00",
        carbs_per_100g="3.00",
    )
    client = authenticate_client(user)

    response = client.post(
        f"/api/v1/meals/{meal.id}/items",
        {
            "food_id": str(food.id),
            "weight_g": "150.00",
        },
        format="json",
    )

    body = response.json()

    assert response.status_code == status.HTTP_201_CREATED
    assert body["data"]["display_name_snapshot"] == "Творог"
    assert body["data"]["weight_g"] == "150.00"
    assert body["data"]["calories_snapshot"] == "180.00"
    assert body["data"]["protein_snapshot"] == "27.00"
    assert body["data"]["fat_snapshot"] == "7.50"
    assert body["data"]["carbs_snapshot"] == "4.50"

    food.name = "Изменённый творог"
    food.calories_per_100g = "999.00"
    food.save()

    meal_item = MealItem.objects.get(id=body["data"]["id"])

    assert meal_item.display_name_snapshot == "Творог"
    assert meal_item.calories_snapshot == 180


@pytest.mark.django_db
def test_add_meal_item_is_idempotent_by_local_device_id_inside_meal():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    meal = Meal.objects.create(
        user=user,
        meal_date="2026-06-18",
        meal_type=MealType.BREAKFAST,
    )
    food = Food.objects.create(
        owner=user,
        name="Творог",
        source=FoodSource.USER,
        calories_per_100g="120.00",
        protein_per_100g="18.00",
        fat_per_100g="5.00",
        carbs_per_100g="3.00",
    )
    client = authenticate_client(user)
    payload = {
        "food_id": str(food.id),
        "weight_g": "150.00",
        "local_device_id": "00000000-0000-0000-0000-000000000001",
        "client_updated_at": "2026-06-18T10:00:00Z",
    }

    first_response = client.post(
        f"/api/v1/meals/{meal.id}/items",
        payload,
        format="json",
    )
    second_response = client.post(
        f"/api/v1/meals/{meal.id}/items",
        payload,
        format="json",
    )

    assert first_response.status_code == status.HTTP_201_CREATED
    assert second_response.status_code == status.HTTP_201_CREATED
    assert second_response.json()["data"]["id"] == first_response.json()["data"]["id"]
    assert MealItem.objects.filter(meal=meal).count() == 1


@pytest.mark.django_db
def test_add_meal_item_by_servings():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    meal = Meal.objects.create(
        user=user,
        meal_date="2026-06-18",
        meal_type=MealType.SNACK,
    )
    food = Food.objects.create(
        owner=user,
        name="Протеин",
        source=FoodSource.USER,
        serving_size="30.00",
        serving_unit="g",
        calories_per_100g="400.00",
        protein_per_100g="80.00",
        fat_per_100g="5.00",
        carbs_per_100g="10.00",
    )
    client = authenticate_client(user)

    response = client.post(
        f"/api/v1/meals/{meal.id}/items",
        {
            "food_id": str(food.id),
            "servings": "2.00",
        },
        format="json",
    )

    body = response.json()

    assert response.status_code == status.HTTP_201_CREATED
    assert body["data"]["servings"] == "2.00"
    assert body["data"]["serving_size_snapshot"] == "30.00"
    assert body["data"]["calories_snapshot"] == "240.00"
    assert body["data"]["protein_snapshot"] == "48.00"


@pytest.mark.django_db
def test_add_meal_item_rejects_other_user_food_and_meal():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    other_user = User.objects.create_user(
        email="other@example.com",
        password="strong-password-123",
    )
    other_meal = Meal.objects.create(
        user=other_user,
        meal_date="2026-06-18",
        meal_type=MealType.BREAKFAST,
    )
    other_food = Food.objects.create(
        owner=other_user,
        name="Чужой продукт",
        source=FoodSource.USER,
        calories_per_100g="100.00",
        protein_per_100g="10.00",
        fat_per_100g="1.00",
        carbs_per_100g="1.00",
    )
    client = authenticate_client(user)

    meal_response = client.post(
        f"/api/v1/meals/{other_meal.id}/items",
        {
            "food_id": str(other_food.id),
            "weight_g": "100.00",
        },
        format="json",
    )

    assert meal_response.status_code == status.HTTP_404_NOT_FOUND
    assert meal_response.json()["error"]["code"] == "NOT_FOUND"

    own_meal = Meal.objects.create(
        user=user,
        meal_date="2026-06-18",
        meal_type=MealType.BREAKFAST,
    )
    food_response = client.post(
        f"/api/v1/meals/{own_meal.id}/items",
        {
            "food_id": str(other_food.id),
            "weight_g": "100.00",
        },
        format="json",
    )

    assert food_response.status_code == status.HTTP_400_BAD_REQUEST
    assert "food_id" in food_response.json()["error"]["fields"]


@pytest.mark.django_db
def test_nutrition_day_returns_meals_and_totals():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    meal = Meal.objects.create(
        user=user,
        meal_date="2026-06-18",
        meal_type=MealType.BREAKFAST,
    )
    other_day_meal = Meal.objects.create(
        user=user,
        meal_date="2026-06-17",
        meal_type=MealType.BREAKFAST,
    )
    food = Food.objects.create(
        owner=user,
        name="Творог",
        source=FoodSource.USER,
        calories_per_100g="120.00",
        protein_per_100g="18.00",
        fat_per_100g="5.00",
        carbs_per_100g="3.00",
    )
    MealItem.objects.create(
        meal=meal,
        food=food,
        display_name_snapshot="Творог",
        weight_g="150.00",
        calories_snapshot="180.00",
        protein_snapshot="27.00",
        fat_snapshot="7.50",
        carbs_snapshot="4.50",
    )
    MealItem.objects.create(
        meal=other_day_meal,
        food=food,
        display_name_snapshot="Творог",
        weight_g="100.00",
        calories_snapshot="120.00",
        protein_snapshot="18.00",
        fat_snapshot="5.00",
        carbs_snapshot="3.00",
    )
    client = authenticate_client(user)

    response = client.get("/api/v1/nutrition/days/2026-06-18")

    body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert body["data"]["date"] == "2026-06-18"
    assert body["data"]["totals"] == {
        "calories": "180.00",
        "protein": "27.00",
        "fat": "7.50",
        "carbs": "4.50",
    }
    assert len(body["data"]["meals"]) == 1
    assert body["data"]["meals"][0]["items"][0]["display_name_snapshot"] == "Творог"


@pytest.mark.django_db
def test_get_meals_filters_by_date_and_type():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    breakfast = Meal.objects.create(
        user=user,
        meal_date="2026-06-18",
        meal_type=MealType.BREAKFAST,
    )
    Meal.objects.create(
        user=user,
        meal_date="2026-06-18",
        meal_type=MealType.DINNER,
    )
    Meal.objects.create(
        user=user,
        meal_date="2026-06-17",
        meal_type=MealType.BREAKFAST,
    )
    client = authenticate_client(user)

    response = client.get("/api/v1/meals?date=2026-06-18&meal_type=breakfast")

    body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert body["meta"]["count"] == 1
    assert body["data"][0]["id"] == str(breakfast.id)


@pytest.mark.django_db
def test_get_meals_supports_limit_offset_pagination():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    Meal.objects.create(
        user=user,
        meal_date="2026-06-19",
        meal_type=MealType.BREAKFAST,
    )
    second = Meal.objects.create(
        user=user,
        meal_date="2026-06-18",
        meal_type=MealType.LUNCH,
    )
    Meal.objects.create(
        user=user,
        meal_date="2026-06-17",
        meal_type=MealType.DINNER,
    )
    client = authenticate_client(user)

    response = client.get("/api/v1/meals?limit=1&offset=1")

    body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert body["meta"] == {
        "count": 1,
        "total_count": 3,
        "limit": 1,
        "offset": 1,
    }
    assert [item["id"] for item in body["data"]] == [str(second.id)]


@pytest.mark.django_db
def test_patch_meal_updates_metadata():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    meal = Meal.objects.create(
        user=user,
        meal_date="2026-06-18",
        meal_type=MealType.BREAKFAST,
    )
    client = authenticate_client(user)

    response = client.patch(
        f"/api/v1/meals/{meal.id}",
        {
            "meal_type": MealType.LUNCH,
            "custom_name": "Обед после тренировки",
            "notes": "Без сахара",
        },
        format="json",
    )

    body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert body["data"]["meal_type"] == MealType.LUNCH
    assert body["data"]["custom_name"] == "Обед после тренировки"
    assert body["data"]["notes"] == "Без сахара"
    assert body["data"]["server_version"] == 2


@pytest.mark.django_db
def test_delete_meal_removes_user_meal():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    meal = Meal.objects.create(
        user=user,
        meal_date="2026-06-18",
        meal_type=MealType.BREAKFAST,
    )
    client = authenticate_client(user)

    response = client.delete(f"/api/v1/meals/{meal.id}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["data"]["success"] is True
    assert not Meal.objects.filter(id=meal.id).exists()


@pytest.mark.django_db
def test_patch_meal_returns_404_for_other_user_meal():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    other_user = User.objects.create_user(
        email="other@example.com",
        password="strong-password-123",
    )
    other_meal = Meal.objects.create(
        user=other_user,
        meal_date="2026-06-18",
        meal_type=MealType.BREAKFAST,
    )
    client = authenticate_client(user)

    response = client.patch(
        f"/api/v1/meals/{other_meal.id}",
        {
            "meal_type": MealType.LUNCH,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.django_db
def test_patch_meal_item_recalculates_snapshot_by_weight():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    meal = Meal.objects.create(
        user=user,
        meal_date="2026-06-18",
        meal_type=MealType.BREAKFAST,
    )
    food = Food.objects.create(
        owner=user,
        name="Рис",
        source=FoodSource.USER,
        calories_per_100g="130.00",
        protein_per_100g="2.70",
        fat_per_100g="0.30",
        carbs_per_100g="28.00",
    )
    meal_item = MealItem.objects.create(
        meal=meal,
        food=food,
        display_name_snapshot="Рис",
        weight_g="100.00",
        calories_snapshot="130.00",
        protein_snapshot="2.70",
        fat_snapshot="0.30",
        carbs_snapshot="28.00",
    )
    client = authenticate_client(user)

    response = client.patch(
        f"/api/v1/meal-items/{meal_item.id}",
        {
            "weight_g": "200.00",
        },
        format="json",
    )

    body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert body["data"]["weight_g"] == "200.00"
    assert body["data"]["servings"] is None
    assert body["data"]["calories_snapshot"] == "260.00"
    assert body["data"]["protein_snapshot"] == "5.40"
    assert body["data"]["server_version"] == 2


@pytest.mark.django_db
def test_patch_meal_item_can_switch_to_servings():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    meal = Meal.objects.create(
        user=user,
        meal_date="2026-06-18",
        meal_type=MealType.SNACK,
    )
    food = Food.objects.create(
        owner=user,
        name="Протеин",
        source=FoodSource.USER,
        serving_size="30.00",
        serving_unit="g",
        calories_per_100g="400.00",
        protein_per_100g="80.00",
        fat_per_100g="5.00",
        carbs_per_100g="10.00",
    )
    meal_item = MealItem.objects.create(
        meal=meal,
        food=food,
        display_name_snapshot="Протеин",
        weight_g="30.00",
        calories_snapshot="120.00",
        protein_snapshot="24.00",
        fat_snapshot="1.50",
        carbs_snapshot="3.00",
    )
    client = authenticate_client(user)

    response = client.patch(
        f"/api/v1/meal-items/{meal_item.id}",
        {
            "weight_g": None,
            "servings": "2.00",
        },
        format="json",
    )

    body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert body["data"]["weight_g"] is None
    assert body["data"]["servings"] == "2.00"
    assert body["data"]["calories_snapshot"] == "240.00"
    assert body["data"]["protein_snapshot"] == "48.00"


@pytest.mark.django_db
def test_delete_meal_item_soft_deletes_and_excludes_from_day_totals():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    meal = Meal.objects.create(
        user=user,
        meal_date="2026-06-18",
        meal_type=MealType.BREAKFAST,
    )
    food = Food.objects.create(
        owner=user,
        name="Творог",
        source=FoodSource.USER,
        calories_per_100g="120.00",
        protein_per_100g="18.00",
        fat_per_100g="5.00",
        carbs_per_100g="3.00",
    )
    meal_item = MealItem.objects.create(
        meal=meal,
        food=food,
        display_name_snapshot="Творог",
        weight_g="150.00",
        calories_snapshot="180.00",
        protein_snapshot="27.00",
        fat_snapshot="7.50",
        carbs_snapshot="4.50",
    )
    client = authenticate_client(user)

    delete_response = client.delete(f"/api/v1/meal-items/{meal_item.id}")
    day_response = client.get("/api/v1/nutrition/days/2026-06-18")

    meal_item.refresh_from_db()

    assert delete_response.status_code == status.HTTP_200_OK
    assert delete_response.json()["data"]["success"] is True
    assert meal_item.deleted_at is not None
    assert meal_item.server_version == 2
    assert day_response.json()["data"]["totals"] == {
        "calories": "0.00",
        "protein": "0.00",
        "fat": "0.00",
        "carbs": "0.00",
    }
    assert day_response.json()["data"]["meals"][0]["items"] == []


@pytest.mark.django_db
def test_patch_meal_item_returns_404_for_other_user_item():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    other_user = User.objects.create_user(
        email="other@example.com",
        password="strong-password-123",
    )
    other_meal = Meal.objects.create(
        user=other_user,
        meal_date="2026-06-18",
        meal_type=MealType.BREAKFAST,
    )
    other_food = Food.objects.create(
        owner=other_user,
        name="Чужой продукт",
        source=FoodSource.USER,
        calories_per_100g="100.00",
        protein_per_100g="10.00",
        fat_per_100g="1.00",
        carbs_per_100g="1.00",
    )
    other_meal_item = MealItem.objects.create(
        meal=other_meal,
        food=other_food,
        display_name_snapshot="Чужой продукт",
        weight_g="100.00",
        calories_snapshot="100.00",
        protein_snapshot="10.00",
        fat_snapshot="1.00",
        carbs_snapshot="1.00",
    )
    client = authenticate_client(user)

    response = client.patch(
        f"/api/v1/meal-items/{other_meal_item.id}",
        {
            "weight_g": "200.00",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.django_db
def test_nutrition_day_includes_active_goal_targets_and_progress():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    goal = UserGoal.objects.create(
        user=user,
        goal_type=GoalType.MUSCLE_GAIN,
        calorie_target=2400,
        protein_target_g="160.00",
        fat_target_g="70.00",
        carbs_target_g="300.00",
        active_from="2026-06-01",
    )
    meal = Meal.objects.create(
        user=user,
        meal_date="2026-06-18",
        meal_type=MealType.BREAKFAST,
    )
    food = Food.objects.create(
        owner=user,
        name="Творог",
        source=FoodSource.USER,
        calories_per_100g="120.00",
        protein_per_100g="18.00",
        fat_per_100g="5.00",
        carbs_per_100g="3.00",
    )
    MealItem.objects.create(
        meal=meal,
        food=food,
        display_name_snapshot="Творог",
        weight_g="200.00",
        calories_snapshot="240.00",
        protein_snapshot="36.00",
        fat_snapshot="10.00",
        carbs_snapshot="6.00",
    )
    client = authenticate_client(user)

    response = client.get("/api/v1/nutrition/days/2026-06-18")

    body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert body["data"]["targets"] == {
        "active_goal_id": str(goal.id),
        "goal_type": GoalType.MUSCLE_GAIN,
        "calories": "2400.00",
        "protein": "160.00",
        "fat": "70.00",
        "carbs": "300.00",
    }
    assert body["data"]["progress"]["calories"] == {
        "consumed": "240.00",
        "target": "2400.00",
        "remaining": "2160.00",
        "percent": "10.00",
    }
    assert body["data"]["progress"]["protein"] == {
        "consumed": "36.00",
        "target": "160.00",
        "remaining": "124.00",
        "percent": "22.50",
    }


@pytest.mark.django_db
def test_nutrition_day_uses_most_recent_goal_active_on_date():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    UserGoal.objects.create(
        user=user,
        goal_type=GoalType.MAINTENANCE,
        calorie_target=2100,
        active_from="2026-01-01",
    )
    active_goal = UserGoal.objects.create(
        user=user,
        goal_type=GoalType.GRADUAL_WEIGHT_LOSS,
        calorie_target=1800,
        active_from="2026-06-01",
        active_to="2026-06-30",
    )
    UserGoal.objects.create(
        user=user,
        goal_type=GoalType.MUSCLE_GAIN,
        calorie_target=2600,
        active_from="2026-07-01",
    )
    client = authenticate_client(user)

    response = client.get("/api/v1/nutrition/days/2026-06-18")

    body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert body["data"]["targets"]["active_goal_id"] == str(active_goal.id)
    assert body["data"]["targets"]["calories"] == "1800.00"


@pytest.mark.django_db
def test_nutrition_day_returns_empty_targets_without_active_goal():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    UserGoal.objects.create(
        user=user,
        goal_type=GoalType.MAINTENANCE,
        calorie_target=2100,
        active_from="2026-01-01",
        active_to="2026-01-31",
    )
    client = authenticate_client(user)

    response = client.get("/api/v1/nutrition/days/2026-06-18")

    body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert body["data"]["targets"] == {
        "active_goal_id": None,
        "goal_type": None,
        "calories": None,
        "protein": None,
        "fat": None,
        "carbs": None,
    }
    assert body["data"]["progress"]["calories"] == {
        "consumed": "0.00",
        "target": None,
        "remaining": None,
        "percent": None,
    }


@pytest.mark.django_db
def test_nutrition_day_rejects_invalid_date():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    client = authenticate_client(user)

    response = client.get("/api/v1/nutrition/days/not-a-date")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "meal_date" in response.json()["error"]["fields"]


@pytest.mark.django_db
def test_create_food_recognition_draft_from_ai_response():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    client = authenticate_client(user)

    response = client.post(
        "/api/v1/nutrition/photo-recognitions",
        {
            "image_key": "private/users/user/photo-1.jpg",
            "raw_ai_response": {
                "items": [
                    {
                        "name": "Омлет",
                        "confidence": 0.84,
                        "weight_g": 180,
                        "calories_per_100g": 154,
                        "protein_per_100g": 11,
                        "fat_per_100g": 12,
                        "carbs_per_100g": 1,
                    }
                ]
            },
        },
        format="json",
    )

    body = response.json()

    assert response.status_code == status.HTTP_201_CREATED
    assert body["data"]["status"] == FoodRecognitionStatus.DRAFT
    assert body["data"]["raw_ai_response"]["items"][0]["name"] == "Омлет"
    assert body["data"]["items"][0]["ai_confidence"] == "0.8400"
    assert body["data"]["items"][0]["corrected_name"] == "Омлет"
    assert body["data"]["items"][0]["totals"] == {
        "calories": "277.20",
        "protein": "19.80",
        "fat": "21.60",
        "carbs": "1.80",
    }

    recognition = FoodRecognition.objects.get(id=body["data"]["id"])

    assert recognition.user == user
    assert recognition.items.count() == 1


@pytest.mark.django_db
def test_create_food_recognition_marks_no_response_as_failed():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    client = authenticate_client(user)

    response = client.post(
        "/api/v1/nutrition/photo-recognitions",
        {
            "image_key": "private/users/user/photo-1.jpg",
            "raw_ai_response": None,
        },
        format="json",
    )

    body = response.json()

    assert response.status_code == status.HTTP_201_CREATED
    assert body["data"]["status"] == FoodRecognitionStatus.FAILED
    assert body["data"]["error_code"] == FoodRecognitionErrorCode.NO_RESPONSE
    assert body["data"]["items"] == []


@pytest.mark.django_db
def test_create_food_recognition_marks_timeout_as_failed():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    client = authenticate_client(user)

    response = client.post(
        "/api/v1/nutrition/photo-recognitions",
        {
            "image_key": "private/users/user/photo-1.jpg",
            "raw_ai_response": "timeout",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["data"]["status"] == FoodRecognitionStatus.FAILED
    assert response.json()["data"]["error_code"] == FoodRecognitionErrorCode.TIMEOUT


@pytest.mark.django_db
def test_create_food_recognition_marks_invalid_ai_format_as_failed():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    client = authenticate_client(user)

    response = client.post(
        "/api/v1/nutrition/photo-recognitions",
        {
            "image_key": "private/users/user/photo-1.jpg",
            "raw_ai_response": {
                "items": [
                    {
                        "name": "Омлет",
                        "confidence": 1.5,
                        "weight_g": 180,
                        "calories_per_100g": 154,
                        "protein_per_100g": 11,
                        "fat_per_100g": 12,
                        "carbs_per_100g": 1,
                    }
                ]
            },
        },
        format="json",
    )

    body = response.json()

    assert response.status_code == status.HTTP_201_CREATED
    assert body["data"]["status"] == FoodRecognitionStatus.FAILED
    assert body["data"]["error_code"] == FoodRecognitionErrorCode.INVALID_FORMAT


@pytest.mark.django_db
def test_patch_food_recognition_item_marks_user_corrected_and_recalculates_totals():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    client = authenticate_client(user)
    create_response = client.post(
        "/api/v1/nutrition/photo-recognitions",
        {
            "image_key": "private/users/user/photo-1.jpg",
            "raw_ai_response": {
                "items": [
                    {
                        "name": "Омлет",
                        "confidence": 0.84,
                        "weight_g": 180,
                        "calories_per_100g": 154,
                        "protein_per_100g": 11,
                        "fat_per_100g": 12,
                        "carbs_per_100g": 1,
                    }
                ]
            },
        },
        format="json",
    )
    recognition_item_id = create_response.json()["data"]["items"][0]["id"]

    response = client.patch(
        f"/api/v1/nutrition/photo-recognition-items/{recognition_item_id}",
        {
            "corrected_name": "Омлет с сыром",
            "corrected_weight_g": "200.00",
            "corrected_calories_per_100g": "180.00",
        },
        format="json",
    )

    body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert body["data"]["corrected_name"] == "Омлет с сыром"
    assert body["data"]["user_corrected"] is True
    assert body["data"]["totals"]["calories"] == "360.00"
    assert body["data"]["totals"]["protein"] == "22.00"


@pytest.mark.django_db
def test_delete_food_recognition_item_removes_draft_item():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    client = authenticate_client(user)
    create_response = client.post(
        "/api/v1/nutrition/photo-recognitions",
        {
            "image_key": "private/users/user/photo-1.jpg",
            "raw_ai_response": {
                "items": [
                    {
                        "name": "Омлет",
                        "confidence": 0.84,
                        "weight_g": 180,
                        "calories_per_100g": 154,
                        "protein_per_100g": 11,
                        "fat_per_100g": 12,
                        "carbs_per_100g": 1,
                    },
                    {
                        "name": "Хлеб",
                        "confidence": 0.75,
                        "weight_g": 40,
                        "calories_per_100g": 250,
                        "protein_per_100g": 8,
                        "fat_per_100g": 3,
                        "carbs_per_100g": 48,
                    },
                ]
            },
        },
        format="json",
    )
    recognition_item_id = create_response.json()["data"]["items"][0]["id"]

    response = client.delete(
        f"/api/v1/nutrition/photo-recognition-items/{recognition_item_id}",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["data"]["success"] is True
    assert not FoodRecognitionItem.objects.filter(id=recognition_item_id).exists()


@pytest.mark.django_db
def test_confirm_food_recognition_creates_meal_items_from_corrected_values():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    client = authenticate_client(user)
    create_response = client.post(
        "/api/v1/nutrition/photo-recognitions",
        {
            "image_key": "private/users/user/photo-1.jpg",
            "raw_ai_response": {
                "items": [
                    {
                        "name": "Омлет",
                        "confidence": 0.84,
                        "weight_g": 180,
                        "calories_per_100g": 154,
                        "protein_per_100g": 11,
                        "fat_per_100g": 12,
                        "carbs_per_100g": 1,
                    }
                ]
            },
        },
        format="json",
    )
    recognition_id = create_response.json()["data"]["id"]
    recognition_item_id = create_response.json()["data"]["items"][0]["id"]
    client.patch(
        f"/api/v1/nutrition/photo-recognition-items/{recognition_item_id}",
        {
            "corrected_name": "Омлет с сыром",
            "corrected_weight_g": "200.00",
            "corrected_calories_per_100g": "180.00",
        },
        format="json",
    )

    response = client.post(
        f"/api/v1/nutrition/photo-recognitions/{recognition_id}/confirm",
        {
            "meal_date": "2026-06-18",
            "meal_type": MealType.BREAKFAST,
            "custom_name": "AI завтрак",
        },
        format="json",
    )

    body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert body["data"]["meal_date"] == "2026-06-18"
    assert body["data"]["custom_name"] == "AI завтрак"
    assert body["data"]["items"][0]["display_name_snapshot"] == "Омлет с сыром"
    assert body["data"]["items"][0]["source"] == MealItemSource.AI
    assert body["data"]["items"][0]["calories_snapshot"] == "360.00"
    assert body["data"]["items"][0]["protein_snapshot"] == "22.00"

    recognition = FoodRecognition.objects.get(id=recognition_id)

    assert recognition.status == FoodRecognitionStatus.CONFIRMED
    assert recognition.confirmed_meal_id == Meal.objects.get(id=body["data"]["id"]).id


@pytest.mark.django_db
def test_confirm_food_recognition_appends_items_to_existing_meal():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    meal = Meal.objects.create(
        user=user,
        meal_date="2026-06-18",
        meal_type=MealType.LUNCH,
    )
    client = authenticate_client(user)
    create_response = client.post(
        "/api/v1/nutrition/photo-recognitions",
        {
            "image_key": "private/users/user/photo-1.jpg",
            "raw_ai_response": {
                "items": [
                    {
                        "name": "Рис",
                        "confidence": 0.70,
                        "weight_g": 100,
                        "calories_per_100g": 130,
                        "protein_per_100g": 2.7,
                        "fat_per_100g": 0.3,
                        "carbs_per_100g": 28,
                    }
                ]
            },
        },
        format="json",
    )
    recognition_id = create_response.json()["data"]["id"]

    response = client.post(
        f"/api/v1/nutrition/photo-recognitions/{recognition_id}/confirm",
        {
            "meal_id": str(meal.id),
        },
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["data"]["id"] == str(meal.id)
    assert meal.items.count() == 1


@pytest.mark.django_db
def test_confirm_food_recognition_rejects_repeated_confirm():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    client = authenticate_client(user)
    create_response = client.post(
        "/api/v1/nutrition/photo-recognitions",
        {
            "image_key": "private/users/user/photo-1.jpg",
            "raw_ai_response": {
                "items": [
                    {
                        "name": "Рис",
                        "confidence": 0.70,
                        "weight_g": 100,
                        "calories_per_100g": 130,
                        "protein_per_100g": 2.7,
                        "fat_per_100g": 0.3,
                        "carbs_per_100g": 28,
                    }
                ]
            },
        },
        format="json",
    )
    recognition_id = create_response.json()["data"]["id"]
    payload = {
        "meal_date": "2026-06-18",
        "meal_type": MealType.LUNCH,
    }

    first_response = client.post(
        f"/api/v1/nutrition/photo-recognitions/{recognition_id}/confirm",
        payload,
        format="json",
    )
    second_response = client.post(
        f"/api/v1/nutrition/photo-recognitions/{recognition_id}/confirm",
        payload,
        format="json",
    )

    assert first_response.status_code == status.HTTP_200_OK
    assert second_response.status_code == status.HTTP_400_BAD_REQUEST
    assert second_response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.django_db
def test_patch_food_recognition_item_rejects_confirmed_recognition():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    client = authenticate_client(user)
    create_response = client.post(
        "/api/v1/nutrition/photo-recognitions",
        {
            "image_key": "private/users/user/photo-1.jpg",
            "raw_ai_response": {
                "items": [
                    {
                        "name": "Рис",
                        "confidence": 0.70,
                        "weight_g": 100,
                        "calories_per_100g": 130,
                        "protein_per_100g": 2.7,
                        "fat_per_100g": 0.3,
                        "carbs_per_100g": 28,
                    }
                ]
            },
        },
        format="json",
    )
    recognition_id = create_response.json()["data"]["id"]
    recognition_item_id = create_response.json()["data"]["items"][0]["id"]
    client.post(
        f"/api/v1/nutrition/photo-recognitions/{recognition_id}/confirm",
        {
            "meal_date": "2026-06-18",
            "meal_type": MealType.LUNCH,
        },
        format="json",
    )

    response = client.patch(
        f"/api/v1/nutrition/photo-recognition-items/{recognition_item_id}",
        {
            "corrected_weight_g": "200.00",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.django_db
def test_delete_food_recognition_item_rejects_confirmed_recognition():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    client = authenticate_client(user)
    create_response = client.post(
        "/api/v1/nutrition/photo-recognitions",
        {
            "image_key": "private/users/user/photo-1.jpg",
            "raw_ai_response": {
                "items": [
                    {
                        "name": "Рис",
                        "confidence": 0.70,
                        "weight_g": 100,
                        "calories_per_100g": 130,
                        "protein_per_100g": 2.7,
                        "fat_per_100g": 0.3,
                        "carbs_per_100g": 28,
                    }
                ]
            },
        },
        format="json",
    )
    recognition_id = create_response.json()["data"]["id"]
    recognition_item_id = create_response.json()["data"]["items"][0]["id"]
    client.post(
        f"/api/v1/nutrition/photo-recognitions/{recognition_id}/confirm",
        {
            "meal_date": "2026-06-18",
            "meal_type": MealType.LUNCH,
        },
        format="json",
    )

    response = client.delete(
        f"/api/v1/nutrition/photo-recognition-items/{recognition_item_id}",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.django_db
def test_get_food_recognition_hides_other_user_recognition():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    other_user = User.objects.create_user(
        email="other@example.com",
        password="strong-password-123",
    )
    other_recognition = FoodRecognition.objects.create(
        user=other_user,
        image_key="private/users/other/photo-1.jpg",
        raw_ai_response={"items": []},
        status=FoodRecognitionStatus.FAILED,
    )
    client = authenticate_client(user)

    response = client.get(f"/api/v1/nutrition/photo-recognitions/{other_recognition.id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.django_db
def test_get_food_recognitions_supports_limit_offset_pagination():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    FoodRecognition.objects.create(
        user=user,
        image_key="private/users/user/photo-1.jpg",
        raw_ai_response={"items": []},
        status=FoodRecognitionStatus.DRAFT,
    )
    second = FoodRecognition.objects.create(
        user=user,
        image_key="private/users/user/photo-2.jpg",
        raw_ai_response={"items": []},
        status=FoodRecognitionStatus.FAILED,
    )
    FoodRecognition.objects.create(
        user=user,
        image_key="private/users/user/photo-3.jpg",
        raw_ai_response={"items": []},
        status=FoodRecognitionStatus.CONFIRMED,
    )
    client = authenticate_client(user)

    response = client.get("/api/v1/nutrition/photo-recognitions?limit=1&offset=1")

    body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert body["meta"] == {
        "count": 1,
        "total_count": 3,
        "limit": 1,
        "offset": 1,
    }
    assert [item["id"] for item in body["data"]] == [str(second.id)]


@pytest.mark.django_db
@override_settings(NUTRITION_AI_PHOTO_PROVIDER="request_payload")
def test_upload_food_recognition_photo_creates_draft_from_provider_payload(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    client = authenticate_client(user)

    response = client.post(
        "/api/v1/nutrition/photo-recognitions/upload",
        {
            "image": build_uploaded_photo(),
            "raw_ai_response": (
                '{"items":[{"name":"Омлет","confidence":0.84,'
                '"weight_g":180,"calories_per_100g":154,'
                '"protein_per_100g":11,"fat_per_100g":12,'
                '"carbs_per_100g":1}]}'
            ),
        },
        format="multipart",
    )

    body = response.json()

    assert response.status_code == status.HTTP_201_CREATED
    assert body["data"]["status"] == FoodRecognitionStatus.DRAFT
    assert body["data"]["image_key"].startswith(
        f"nutrition/photo-recognitions/{user.id}/"
    )
    assert default_storage.exists(body["data"]["image_key"]) is False
    assert body["data"]["items"][0]["corrected_name"] == "Омлет"


@pytest.mark.django_db
@override_settings(NUTRITION_AI_PHOTO_PROVIDER="disabled")
def test_upload_food_recognition_photo_with_disabled_provider_returns_failed_draft(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    client = authenticate_client(user)

    response = client.post(
        "/api/v1/nutrition/photo-recognitions/upload",
        {
            "image": build_uploaded_photo(),
        },
        format="multipart",
    )

    body = response.json()

    assert response.status_code == status.HTTP_201_CREATED
    assert body["data"]["status"] == FoodRecognitionStatus.FAILED
    assert body["data"]["error_code"] == FoodRecognitionErrorCode.NO_RESPONSE
    assert body["data"]["error_message"] == "AI-распознавание отключено на backend"
    assert default_storage.exists(body["data"]["image_key"]) is False


@pytest.mark.django_db
@override_settings(NUTRITION_AI_PHOTO_PROVIDER="disabled")
def test_upload_food_recognition_photo_is_rate_limited(settings, tmp_path, monkeypatch):
    cache.clear()
    monkeypatch.setitem(
        ScopedRateThrottle.THROTTLE_RATES,
        "ai_photo_upload",
        "1/min",
    )
    settings.MEDIA_ROOT = tmp_path
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    client = authenticate_client(user)

    first_response = client.post(
        "/api/v1/nutrition/photo-recognitions/upload",
        {
            "image": build_uploaded_photo(name="meal-1.jpg"),
        },
        format="multipart",
    )
    second_response = client.post(
        "/api/v1/nutrition/photo-recognitions/upload",
        {
            "image": build_uploaded_photo(name="meal-2.jpg"),
        },
        format="multipart",
    )

    assert first_response.status_code == status.HTTP_201_CREATED
    assert second_response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert second_response.json()["error"]["code"] == "THROTTLED"


@pytest.mark.django_db
def test_upload_food_recognition_photo_rejects_unsupported_content_type(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    client = authenticate_client(user)

    response = client.post(
        "/api/v1/nutrition/photo-recognitions/upload",
        {
            "image": build_uploaded_photo(
                name="meal.txt",
                content_type="text/plain",
            ),
        },
        format="multipart",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "image" in response.json()["error"]["fields"]


@pytest.mark.django_db
@override_settings(NUTRITION_AI_PHOTO_MAX_BYTES=4)
def test_upload_food_recognition_photo_rejects_too_large_file(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    client = authenticate_client(user)

    response = client.post(
        "/api/v1/nutrition/photo-recognitions/upload",
        {
            "image": build_uploaded_photo(content=b"12345"),
        },
        format="multipart",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "image" in response.json()["error"]["fields"]


@pytest.mark.django_db
@override_settings(NUTRITION_AI_PHOTO_PROVIDER="request_payload")
def test_upload_food_recognition_photo_rejects_invalid_raw_ai_response_json(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    settings.NUTRITION_AI_PHOTO_MAX_BYTES = 5 * 1024 * 1024
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    client = authenticate_client(user)

    response = client.post(
        "/api/v1/nutrition/photo-recognitions/upload",
        {
            "image": build_uploaded_photo(),
            "raw_ai_response": "{broken-json",
        },
        format="multipart",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "raw_ai_response" in response.json()["error"]["fields"]

@pytest.mark.django_db
def test_get_food_detail_returns_visible_system_food():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    food = Food.objects.create(
        name="Рис",
        source=FoodSource.SYSTEM,
        calories_per_100g="130.00",
        protein_per_100g="2.70",
        fat_per_100g="0.30",
        carbs_per_100g="28.00",
    )
    client = authenticate_client(user)

    response = client.get(f"/api/v1/foods/{food.id}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["data"]["id"] == str(food.id)


@pytest.mark.django_db
def test_get_foods_filters_by_barcode_source_and_verified():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    matching_food = Food.objects.create(
        owner=user,
        name="Протеин",
        barcode="123456",
        source=FoodSource.USER,
        is_verified=True,
        calories_per_100g="400.00",
        protein_per_100g="80.00",
        fat_per_100g="5.00",
        carbs_per_100g="10.00",
    )
    Food.objects.create(
        owner=user,
        name="Другой протеин",
        barcode="999999",
        source=FoodSource.USER,
        is_verified=False,
        calories_per_100g="390.00",
        protein_per_100g="75.00",
        fat_per_100g="6.00",
        carbs_per_100g="12.00",
    )
    client = authenticate_client(user)

    response = client.get("/api/v1/foods?barcode=123456&source=user&is_verified=true")

    body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert body["meta"]["count"] == 1
    assert body["data"][0]["id"] == str(matching_food.id)


@pytest.mark.django_db
def test_patch_food_updates_owned_user_food():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    food = Food.objects.create(
        owner=user,
        name="Творог",
        source=FoodSource.USER,
        calories_per_100g="120.00",
        protein_per_100g="18.00",
        fat_per_100g="5.00",
        carbs_per_100g="3.00",
    )
    client = authenticate_client(user)

    response = client.patch(
        f"/api/v1/foods/{food.id}",
        {
            "name": "Творог 5%",
            "calories_per_100g": "130.00",
        },
        format="json",
    )

    body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert body["data"]["name"] == "Творог 5%"
    assert body["data"]["calories_per_100g"] == "130.00"

    food.refresh_from_db()

    assert food.name == "Творог 5%"
    assert food.calories_per_100g == 130


@pytest.mark.django_db
def test_patch_food_returns_404_for_system_food():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    food = Food.objects.create(
        name="Рис",
        source=FoodSource.SYSTEM,
        calories_per_100g="130.00",
        protein_per_100g="2.70",
        fat_per_100g="0.30",
        carbs_per_100g="28.00",
    )
    client = authenticate_client(user)

    response = client.patch(
        f"/api/v1/foods/{food.id}",
        {
            "name": "Новый рис",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.django_db
def test_patch_food_returns_404_for_other_user_food():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    other_user = User.objects.create_user(
        email="other@example.com",
        password="strong-password-123",
    )
    food = Food.objects.create(
        owner=other_user,
        name="Чужой продукт",
        source=FoodSource.USER,
        calories_per_100g="100.00",
        protein_per_100g="10.00",
        fat_per_100g="1.00",
        carbs_per_100g="1.00",
    )
    client = authenticate_client(user)

    response = client.patch(
        f"/api/v1/foods/{food.id}",
        {
            "name": "Попытка изменения",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.django_db
def test_delete_food_soft_deletes_owned_user_food():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    food = Food.objects.create(
        owner=user,
        name="Творог",
        source=FoodSource.USER,
        calories_per_100g="120.00",
        protein_per_100g="18.00",
        fat_per_100g="5.00",
        carbs_per_100g="3.00",
    )
    client = authenticate_client(user)

    response = client.delete(f"/api/v1/foods/{food.id}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["data"]["success"] is True

    food.refresh_from_db()

    assert food.is_active is False

    list_response = client.get("/api/v1/foods")

    assert str(food.id) not in {
        item["id"]
        for item in list_response.json()["data"]
    }

@pytest.mark.django_db
def test_get_foods_supports_limit_and_offset():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )

    first_food = Food.objects.create(
        owner=user,
        name="Apple",
        source=FoodSource.USER,
        calories_per_100g="52.00",
        protein_per_100g="0.30",
        fat_per_100g="0.20",
        carbs_per_100g="14.00",
    )
    second_food = Food.objects.create(
        owner=user,
        name="Banana",
        source=FoodSource.USER,
        calories_per_100g="89.00",
        protein_per_100g="1.10",
        fat_per_100g="0.30",
        carbs_per_100g="23.00",
    )

    client = authenticate_client(user)

    response = client.get("/api/v1/foods?limit=1&offset=1")

    body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert body["meta"]["count"] == 1
    assert body["meta"]["total_count"] == 2
    assert body["meta"]["limit"] == 1
    assert body["meta"]["offset"] == 1
    assert body["data"][0]["id"] == str(second_food.id)


@pytest.mark.django_db
def test_get_foods_rejects_invalid_source_filter():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    client = authenticate_client(user)

    response = client.get("/api/v1/foods?source=wrong")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "source" in response.json()["error"]["fields"]


@pytest.mark.django_db
def test_get_foods_rejects_too_large_limit():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    client = authenticate_client(user)

    response = client.get("/api/v1/foods?limit=1000")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "limit" in response.json()["error"]["fields"]


@pytest.mark.django_db
def test_create_food_rejects_duplicate_active_user_barcode():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    Food.objects.create(
        owner=user,
        name="Протеин",
        barcode="123456",
        source=FoodSource.USER,
        calories_per_100g="400.00",
        protein_per_100g="80.00",
        fat_per_100g="5.00",
        carbs_per_100g="10.00",
    )
    client = authenticate_client(user)

    response = client.post(
        "/api/v1/foods",
        {
            "name": "Другой протеин",
            "barcode": "123456",
            "calories_per_100g": "390.00",
            "protein_per_100g": "75.00",
            "fat_per_100g": "6.00",
            "carbs_per_100g": "12.00",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "barcode" in response.json()["error"]["fields"]


@pytest.mark.django_db
def test_create_food_allows_reusing_barcode_after_soft_delete():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    Food.objects.create(
        owner=user,
        name="Старый протеин",
        barcode="123456",
        source=FoodSource.USER,
        is_active=False,
        calories_per_100g="400.00",
        protein_per_100g="80.00",
        fat_per_100g="5.00",
        carbs_per_100g="10.00",
    )
    client = authenticate_client(user)

    response = client.post(
        "/api/v1/foods",
        {
            "name": "Новый протеин",
            "barcode": "123456",
            "calories_per_100g": "390.00",
            "protein_per_100g": "75.00",
            "fat_per_100g": "6.00",
            "carbs_per_100g": "12.00",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["data"]["barcode"] == "123456"


@pytest.mark.django_db
def test_patch_food_rejects_duplicate_active_user_barcode():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    Food.objects.create(
        owner=user,
        name="Протеин",
        barcode="123456",
        source=FoodSource.USER,
        calories_per_100g="400.00",
        protein_per_100g="80.00",
        fat_per_100g="5.00",
        carbs_per_100g="10.00",
    )
    food = Food.objects.create(
        owner=user,
        name="Творог",
        barcode="777777",
        source=FoodSource.USER,
        calories_per_100g="120.00",
        protein_per_100g="18.00",
        fat_per_100g="5.00",
        carbs_per_100g="3.00",
    )
    client = authenticate_client(user)

    response = client.patch(
        f"/api/v1/foods/{food.id}",
        {
            "barcode": "123456",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "barcode" in response.json()["error"]["fields"]
