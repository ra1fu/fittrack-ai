from datetime import datetime, timezone

import pytest
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User
from exercises.models import Exercise, ExerciseTrackingType, MuscleGroup
from nutrition.models import Food, FoodSource, Meal, MealItem, MealType
from profiles.models import GoalType, UserGoal
from workouts.models import (
    Workout,
    WorkoutExercise,
    WorkoutSet,
    WorkoutSetType,
    WorkoutStatus,
)


def authenticate_client(user):
    access = str(RefreshToken.for_user(user).access_token)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return client


@pytest.mark.django_db
def test_dashboard_summary_returns_nutrition_and_weekly_workout_stats():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    UserGoal.objects.create(
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
    chest = MuscleGroup.objects.create(code="chest", name="Грудь")
    exercise = Exercise.objects.create(
        name="Жим лёжа",
        primary_muscle_group=chest,
        tracking_type=ExerciseTrackingType.WEIGHT_REPS,
        is_system=True,
    )
    workout = Workout.objects.create(
        user=user,
        name="Push",
        status=WorkoutStatus.COMPLETED,
        started_at=datetime(2026, 6, 17, 10, 0, tzinfo=timezone.utc),
        finished_at=datetime(2026, 6, 17, 11, 0, tzinfo=timezone.utc),
        duration_seconds=3600,
    )
    workout_exercise = WorkoutExercise.objects.create(
        workout=workout,
        exercise=exercise,
        position=1,
    )
    WorkoutSet.objects.create(
        workout_exercise=workout_exercise,
        position=1,
        set_type=WorkoutSetType.WORKING,
        weight="100.00",
        repetitions=5,
        is_completed=True,
    )
    Workout.objects.create(
        user=user,
        name="Old workout",
        status=WorkoutStatus.COMPLETED,
        started_at=datetime(2026, 6, 10, 10, 0, tzinfo=timezone.utc),
        duration_seconds=1800,
    )
    client = authenticate_client(user)

    response = client.get("/api/v1/dashboard/summary?date=2026-06-18")

    body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert body["data"]["date"] == "2026-06-18"
    assert body["data"]["nutrition"]["meal_count"] == 1
    assert body["data"]["nutrition"]["totals"]["calories"] == "240.00"
    assert body["data"]["nutrition"]["targets"]["calories"] == "2400.00"
    assert body["data"]["nutrition"]["progress"]["calories"]["percent"] == "10.00"
    assert body["data"]["workouts"] == {
        "week_start": "2026-06-15",
        "week_end": "2026-06-21",
        "completed_workouts": 1,
        "total_volume": "500.00",
        "completed_working_sets": 1,
        "duration_seconds": 3600,
    }


@pytest.mark.django_db
def test_dashboard_summary_requires_authentication():
    client = APIClient()

    response = client.get("/api/v1/dashboard/summary?date=2026-06-18")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["error"]["code"] == "NOT_AUTHENTICATED"


@pytest.mark.django_db
def test_dashboard_summary_rejects_invalid_date():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    client = authenticate_client(user)

    response = client.get("/api/v1/dashboard/summary?date=wrong")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "date" in response.json()["error"]["fields"]


@pytest.mark.django_db
def test_dashboard_trends_returns_daily_points_for_period():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    first_meal = Meal.objects.create(
        user=user,
        meal_date="2026-06-17",
        meal_type=MealType.BREAKFAST,
    )
    second_meal = Meal.objects.create(
        user=user,
        meal_date="2026-06-19",
        meal_type=MealType.DINNER,
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
    MealItem.objects.create(
        meal=first_meal,
        food=food,
        display_name_snapshot="Рис",
        weight_g="100.00",
        calories_snapshot="130.00",
        protein_snapshot="2.70",
        fat_snapshot="0.30",
        carbs_snapshot="28.00",
    )
    MealItem.objects.create(
        meal=second_meal,
        food=food,
        display_name_snapshot="Рис",
        weight_g="200.00",
        calories_snapshot="260.00",
        protein_snapshot="5.40",
        fat_snapshot="0.60",
        carbs_snapshot="56.00",
    )
    chest = MuscleGroup.objects.create(code="chest", name="Грудь")
    exercise = Exercise.objects.create(
        name="Жим лёжа",
        primary_muscle_group=chest,
        tracking_type=ExerciseTrackingType.WEIGHT_REPS,
        is_system=True,
    )
    workout = Workout.objects.create(
        user=user,
        name="Push",
        status=WorkoutStatus.COMPLETED,
        started_at=datetime(2026, 6, 19, 10, 0, tzinfo=timezone.utc),
        duration_seconds=2400,
    )
    workout_exercise = WorkoutExercise.objects.create(
        workout=workout,
        exercise=exercise,
        position=1,
    )
    WorkoutSet.objects.create(
        workout_exercise=workout_exercise,
        position=1,
        set_type=WorkoutSetType.WORKING,
        weight="80.00",
        repetitions=8,
        is_completed=True,
    )
    Workout.objects.create(
        user=user,
        name="Cancelled",
        status=WorkoutStatus.CANCELLED,
        started_at=datetime(2026, 6, 19, 12, 0, tzinfo=timezone.utc),
        duration_seconds=1200,
    )
    client = authenticate_client(user)

    response = client.get(
        "/api/v1/dashboard/trends?date_from=2026-06-17&date_to=2026-06-19"
    )

    body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert body["data"]["date_from"] == "2026-06-17"
    assert body["data"]["date_to"] == "2026-06-19"
    assert body["data"]["points"] == [
        {
            "date": "2026-06-17",
            "nutrition": {
                "calories": "130.00",
                "protein": "2.70",
                "fat": "0.30",
                "carbs": "28.00",
                "meal_count": 1,
            },
            "workouts": {
                "completed_workouts": 0,
                "total_volume": "0.00",
                "completed_working_sets": 0,
                "duration_seconds": 0,
            },
        },
        {
            "date": "2026-06-18",
            "nutrition": {
                "calories": "0.00",
                "protein": "0.00",
                "fat": "0.00",
                "carbs": "0.00",
                "meal_count": 0,
            },
            "workouts": {
                "completed_workouts": 0,
                "total_volume": "0.00",
                "completed_working_sets": 0,
                "duration_seconds": 0,
            },
        },
        {
            "date": "2026-06-19",
            "nutrition": {
                "calories": "260.00",
                "protein": "5.40",
                "fat": "0.60",
                "carbs": "56.00",
                "meal_count": 1,
            },
            "workouts": {
                "completed_workouts": 1,
                "total_volume": "640.00",
                "completed_working_sets": 1,
                "duration_seconds": 2400,
            },
        },
    ]


@pytest.mark.django_db
def test_dashboard_trends_rejects_missing_date_from():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    client = authenticate_client(user)

    response = client.get("/api/v1/dashboard/trends?date_to=2026-06-19")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "date_from" in response.json()["error"]["fields"]


@pytest.mark.django_db
def test_dashboard_trends_rejects_reversed_period():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    client = authenticate_client(user)

    response = client.get(
        "/api/v1/dashboard/trends?date_from=2026-06-20&date_to=2026-06-19"
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "date_to" in response.json()["error"]["fields"]


@pytest.mark.django_db
def test_dashboard_trends_rejects_too_large_period():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    client = authenticate_client(user)

    response = client.get(
        "/api/v1/dashboard/trends?date_from=2026-01-01&date_to=2026-04-30"
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "date_to" in response.json()["error"]["fields"]
