from datetime import date
from decimal import Decimal

import pytest
from django.db import IntegrityError
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User
from profiles.models import (
    ExperienceLevel,
    GoalType,
    UnitSystem,
    UserGoal,
    UserProfile,
    Weekday,
)


@pytest.mark.django_db
def test_create_user_profile_with_defaults():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )

    profile = UserProfile.objects.create(user=user)

    assert profile.user == user
    assert profile.display_name == ""
    assert profile.experience_level == ExperienceLevel.BEGINNER
    assert profile.timezone == "UTC"
    assert profile.locale == "ru"
    assert profile.unit_system == UnitSystem.METRIC
    assert profile.week_starts_on == Weekday.MONDAY


@pytest.mark.django_db
def test_user_profile_is_one_to_one_with_user():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )

    UserProfile.objects.create(user=user)

    with pytest.raises(IntegrityError):
        UserProfile.objects.create(user=user)


@pytest.mark.django_db
def test_create_user_goal_with_valid_targets():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )

    goal = UserGoal.objects.create(
        user=user,
        goal_type=GoalType.STRENGTH,
        calorie_target=2500,
        protein_target_g=Decimal("180.00"),
        fat_target_g=Decimal("80.00"),
        carbs_target_g=Decimal("260.00"),
        workouts_per_week=4,
        target_weight_min=Decimal("85.00"),
        target_weight_max=Decimal("90.00"),
        active_from=date(2026, 6, 17),
    )

    assert goal.user == user
    assert goal.goal_type == GoalType.STRENGTH
    assert goal.calorie_target == 2500
    assert goal.workouts_per_week == 4
    assert goal.active_to is None


@pytest.mark.django_db
def test_user_goal_allows_multiple_historical_goals():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )

    UserGoal.objects.create(
        user=user,
        goal_type=GoalType.MAINTENANCE,
        active_from=date(2026, 1, 1),
        active_to=date(2026, 6, 1),
    )
    UserGoal.objects.create(
        user=user,
        goal_type=GoalType.STRENGTH,
        active_from=date(2026, 6, 2),
    )

    assert UserGoal.objects.filter(user=user).count() == 2

def test_me_requires_authentication(db):
    client = APIClient()

    response = client.get("/api/v1/me")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["error"]["code"] == "NOT_AUTHENTICATED"


def test_me_returns_current_user_and_profile(db):
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    UserProfile.objects.create(
        user=user,
        display_name="Rauan",
        timezone="Asia/Almaty",
        locale="ru",
    )

    access = str(RefreshToken.for_user(user).access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.get("/api/v1/me")

    body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert body["data"]["user"]["id"] == str(user.id)
    assert body["data"]["user"]["email"] == "user@example.com"
    assert body["data"]["user"]["email_verified"] is False
    assert body["data"]["profile"]["display_name"] == "Rauan"
    assert body["data"]["profile"]["timezone"] == "Asia/Almaty"
    assert body["data"]["profile"]["locale"] == "ru"


def test_me_returns_only_authenticated_user_data(db):
    first_user = User.objects.create_user(
        email="first@example.com",
        password="strong-password-123",
    )
    second_user = User.objects.create_user(
        email="second@example.com",
        password="strong-password-123",
    )

    UserProfile.objects.create(user=first_user, display_name="First")
    UserProfile.objects.create(user=second_user, display_name="Second")

    access = str(RefreshToken.for_user(first_user).access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.get("/api/v1/me")

    body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert body["data"]["user"]["email"] == "first@example.com"
    assert body["data"]["profile"]["display_name"] == "First"
    assert body["data"]["user"]["email"] != "second@example.com"
    assert body["data"]["profile"]["display_name"] != "Second"

def test_patch_me_updates_current_user_profile(db):
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    UserProfile.objects.create(user=user)

    access = str(RefreshToken.for_user(user).access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.patch(
        "/api/v1/me",
        {
            "display_name": "Rauan",
            "height_cm": "180.50",
            "timezone": "Asia/Almaty",
            "locale": "ru",
            "unit_system": "metric",
            "week_starts_on": "monday",
            "experience_level": "intermediate",
        },
        format="json",
    )

    body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert body["data"]["profile"]["display_name"] == "Rauan"
    assert body["data"]["profile"]["height_cm"] == "180.50"
    assert body["data"]["profile"]["timezone"] == "Asia/Almaty"
    assert body["data"]["profile"]["experience_level"] == "intermediate"

    user.profile.refresh_from_db()

    assert user.profile.display_name == "Rauan"


def test_patch_me_creates_missing_profile(db):
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    access = str(RefreshToken.for_user(user).access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.patch(
        "/api/v1/me",
        {
            "display_name": "Rauan",
        },
        format="json",
    )

    body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert body["data"]["profile"]["display_name"] == "Rauan"
    assert UserProfile.objects.filter(user=user, display_name="Rauan").exists()


def test_patch_me_requires_authentication(db):
    client = APIClient()

    response = client.patch(
        "/api/v1/me",
        {
            "display_name": "Rauan",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["error"]["code"] == "NOT_AUTHENTICATED"


def test_patch_me_rejects_invalid_height(db):
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    UserProfile.objects.create(user=user)

    access = str(RefreshToken.for_user(user).access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.patch(
        "/api/v1/me",
        {
            "height_cm": "-10",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "height_cm" in response.json()["error"]["fields"]


def test_patch_me_rejects_invalid_timezone(db):
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    UserProfile.objects.create(user=user)

    access = str(RefreshToken.for_user(user).access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.patch(
        "/api/v1/me",
        {
            "timezone": "Not/A_Timezone",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "timezone" in response.json()["error"]["fields"]


def test_patch_me_does_not_change_user_email(db):
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    UserProfile.objects.create(user=user)

    access = str(RefreshToken.for_user(user).access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.patch(
        "/api/v1/me",
        {
            "email": "new@example.com",
            "display_name": "Rauan",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK

    user.refresh_from_db()

    assert user.email == "user@example.com"
    assert user.profile.display_name == "Rauan"

def test_get_me_goals_requires_authentication(db):
    client = APIClient()

    response = client.get("/api/v1/me/goals")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["error"]["code"] == "NOT_AUTHENTICATED"


def test_get_me_goals_returns_only_current_user_goals(db):
    first_user = User.objects.create_user(
        email="first@example.com",
        password="strong-password-123",
    )
    second_user = User.objects.create_user(
        email="second@example.com",
        password="strong-password-123",
    )

    first_goal = UserGoal.objects.create(
        user=first_user,
        goal_type=GoalType.STRENGTH,
        active_from=date(2026, 6, 17),
    )
    UserGoal.objects.create(
        user=second_user,
        goal_type=GoalType.MUSCLE_GAIN,
        active_from=date(2026, 6, 17),
    )

    access = str(RefreshToken.for_user(first_user).access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.get("/api/v1/me/goals")

    body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(body["data"]) == 1
    assert body["data"][0]["id"] == str(first_goal.id)
    assert body["data"][0]["goal_type"] == GoalType.STRENGTH


def test_create_me_goal_successfully(db):
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )

    access = str(RefreshToken.for_user(user).access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.post(
        "/api/v1/me/goals",
        {
            "goal_type": "strength",
            "calorie_target": 2500,
            "protein_target_g": "180.00",
            "fat_target_g": "80.00",
            "carbs_target_g": "260.00",
            "workouts_per_week": 4,
            "target_weight_min": "85.00",
            "target_weight_max": "90.00",
            "active_from": "2026-06-17",
        },
        format="json",
    )

    body = response.json()

    assert response.status_code == status.HTTP_201_CREATED
    assert body["data"]["goal_type"] == "strength"
    assert body["data"]["calorie_target"] == 2500
    assert body["data"]["protein_target_g"] == "180.00"

    goal = UserGoal.objects.get(id=body["data"]["id"])

    assert goal.user == user


def test_create_me_goal_rejects_invalid_weight_range(db):
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )

    access = str(RefreshToken.for_user(user).access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.post(
        "/api/v1/me/goals",
        {
            "goal_type": "strength",
            "target_weight_min": "95.00",
            "target_weight_max": "90.00",
            "active_from": "2026-06-17",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "target_weight_min" in response.json()["error"]["fields"]


def test_create_me_goal_rejects_invalid_active_period(db):
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )

    access = str(RefreshToken.for_user(user).access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.post(
        "/api/v1/me/goals",
        {
            "goal_type": "strength",
            "active_from": "2026-06-17",
            "active_to": "2026-06-16",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "active_to" in response.json()["error"]["fields"]


def test_create_me_goal_ignores_user_id_from_payload(db):
    first_user = User.objects.create_user(
        email="first@example.com",
        password="strong-password-123",
    )
    second_user = User.objects.create_user(
        email="second@example.com",
        password="strong-password-123",
    )

    access = str(RefreshToken.for_user(first_user).access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.post(
        "/api/v1/me/goals",
        {
            "user": str(second_user.id),
            "goal_type": "strength",
            "active_from": "2026-06-17",
        },
        format="json",
    )

    body = response.json()

    assert response.status_code == status.HTTP_201_CREATED

    goal = UserGoal.objects.get(id=body["data"]["id"])

    assert goal.user == first_user
    assert goal.user != second_user


def test_patch_me_goal_updates_current_user_goal(db):
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    goal = UserGoal.objects.create(
        user=user,
        goal_type=GoalType.STRENGTH,
        calorie_target=2500,
        active_from=date(2026, 6, 18),
    )

    access = str(RefreshToken.for_user(user).access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.patch(
        f"/api/v1/me/goals/{goal.id}",
        {
            "calorie_target": 2700,
            "workouts_per_week": 5,
            "target_weight_min": "86.00",
            "target_weight_max": "91.00",
        },
        format="json",
    )

    body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert body["data"]["calorie_target"] == 2700
    assert body["data"]["workouts_per_week"] == 5
    assert body["data"]["target_weight_min"] == "86.00"
    assert body["data"]["target_weight_max"] == "91.00"

    goal.refresh_from_db()

    assert goal.calorie_target == 2700
    assert goal.workouts_per_week == 5


def test_patch_me_goal_requires_authentication(db):
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    goal = UserGoal.objects.create(
        user=user,
        goal_type=GoalType.STRENGTH,
        active_from=date(2026, 6, 18),
    )

    client = APIClient()

    response = client.patch(
        f"/api/v1/me/goals/{goal.id}",
        {
            "calorie_target": 2700,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["error"]["code"] == "NOT_AUTHENTICATED"


def test_patch_me_goal_returns_404_for_other_user_goal(db):
    first_user = User.objects.create_user(
        email="first@example.com",
        password="strong-password-123",
    )
    second_user = User.objects.create_user(
        email="second@example.com",
        password="strong-password-123",
    )

    second_goal = UserGoal.objects.create(
        user=second_user,
        goal_type=GoalType.MUSCLE_GAIN,
        active_from=date(2026, 6, 18),
    )

    access = str(RefreshToken.for_user(first_user).access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.patch(
        f"/api/v1/me/goals/{second_goal.id}",
        {
            "calorie_target": 3000,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["error"]["code"] == "NOT_FOUND"

    second_goal.refresh_from_db()

    assert second_goal.calorie_target is None


def test_patch_me_goal_rejects_invalid_weight_range(db):
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    goal = UserGoal.objects.create(
        user=user,
        goal_type=GoalType.STRENGTH,
        active_from=date(2026, 6, 18),
    )

    access = str(RefreshToken.for_user(user).access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.patch(
        f"/api/v1/me/goals/{goal.id}",
        {
            "target_weight_min": "95.00",
            "target_weight_max": "90.00",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "target_weight_min" in response.json()["error"]["fields"]


def test_patch_me_goal_rejects_invalid_active_period(db):
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    goal = UserGoal.objects.create(
        user=user,
        goal_type=GoalType.STRENGTH,
        active_from=date(2026, 6, 18),
    )

    access = str(RefreshToken.for_user(user).access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.patch(
        f"/api/v1/me/goals/{goal.id}",
        {
            "active_from": "2026-06-18",
            "active_to": "2026-06-17",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "active_to" in response.json()["error"]["fields"]


def test_patch_me_goal_ignores_user_id_from_payload(db):
    first_user = User.objects.create_user(
        email="first@example.com",
        password="strong-password-123",
    )
    second_user = User.objects.create_user(
        email="second@example.com",
        password="strong-password-123",
    )

    goal = UserGoal.objects.create(
        user=first_user,
        goal_type=GoalType.STRENGTH,
        active_from=date(2026, 6, 18),
    )

    access = str(RefreshToken.for_user(first_user).access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.patch(
        f"/api/v1/me/goals/{goal.id}",
        {
            "user": str(second_user.id),
            "goal_type": "muscle_gain",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK

    goal.refresh_from_db()

    assert goal.user == first_user
    assert goal.user != second_user
    assert goal.goal_type == GoalType.MUSCLE_GAIN
