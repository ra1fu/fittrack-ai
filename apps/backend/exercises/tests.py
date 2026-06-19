import pytest
from rest_framework import status
from rest_framework.test import APIClient
from accounts.models import User
from exercises.models import Equipment, Exercise, ExerciseTrackingType, MuscleGroup
from rest_framework_simplejwt.tokens import RefreshToken


@pytest.mark.django_db
def test_get_muscle_groups_returns_active_items_sorted_by_name():
    MuscleGroup.objects.create(code="back", name="Спина")
    MuscleGroup.objects.create(code="chest", name="Грудь")
    MuscleGroup.objects.create(code="inactive", name="Неактивная", is_active=False)

    client = APIClient()

    response = client.get("/api/v1/muscle-groups")

    body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert [item["name"] for item in body["data"]] == ["Грудь", "Спина"]
    assert all(item["code"] != "inactive" for item in body["data"])


@pytest.mark.django_db
def test_get_equipment_returns_active_items_sorted_by_name():
    Equipment.objects.create(code="barbell", name="Штанга")
    Equipment.objects.create(code="dumbbell", name="Гантели")
    Equipment.objects.create(code="inactive", name="Неактивное", is_active=False)

    client = APIClient()

    response = client.get("/api/v1/equipment")

    body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert [item["name"] for item in body["data"]] == ["Гантели", "Штанга"]
    assert all(item["code"] != "inactive" for item in body["data"])


@pytest.mark.django_db
def test_muscle_group_can_have_parent():
    parent = MuscleGroup.objects.create(code="legs", name="Ноги")
    child = MuscleGroup.objects.create(
        code="quadriceps",
        name="Квадрицепс",
        parent=parent,
    )

    client = APIClient()

    response = client.get("/api/v1/muscle-groups")

    body = response.json()
    quadriceps = next(item for item in body["data"] if item["code"] == "quadriceps")

    assert response.status_code == status.HTTP_200_OK
    assert quadriceps["parent_id"] == str(parent.id)

@pytest.mark.django_db
def test_get_exercises_returns_active_system_exercises_for_anonymous_user():
    chest = MuscleGroup.objects.create(code="chest", name="Грудь")
    barbell = Equipment.objects.create(code="barbell", name="Штанга")

    Exercise.objects.create(
        name="Жим лёжа",
        primary_muscle_group=chest,
        equipment=barbell,
        tracking_type=ExerciseTrackingType.WEIGHT_REPS,
        is_system=True,
    )
    Exercise.objects.create(
        name="Неактивное упражнение",
        primary_muscle_group=chest,
        equipment=barbell,
        is_system=True,
        is_active=False,
    )

    client = APIClient()

    response = client.get("/api/v1/exercises")

    body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(body["data"]) == 1
    assert body["data"][0]["name"] == "Жим лёжа"


@pytest.mark.django_db
def test_get_exercises_includes_current_user_custom_exercises():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    other_user = User.objects.create_user(
        email="other@example.com",
        password="strong-password-123",
    )

    back = MuscleGroup.objects.create(code="back", name="Спина")
    dumbbell = Equipment.objects.create(code="dumbbell", name="Гантели")

    Exercise.objects.create(
        name="Системная тяга",
        primary_muscle_group=back,
        equipment=dumbbell,
        is_system=True,
    )
    Exercise.objects.create(
        name="Моя тяга",
        owner=user,
        primary_muscle_group=back,
        equipment=dumbbell,
        is_system=False,
    )
    Exercise.objects.create(
        name="Чужая тяга",
        owner=other_user,
        primary_muscle_group=back,
        equipment=dumbbell,
        is_system=False,
    )

    access = str(RefreshToken.for_user(user).access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.get("/api/v1/exercises")

    names = [item["name"] for item in response.json()["data"]]

    assert response.status_code == status.HTTP_200_OK
    assert names == ["Моя тяга", "Системная тяга"]


@pytest.mark.django_db
def test_get_exercises_filters_by_search_muscle_group_equipment_and_tracking_type():
    chest = MuscleGroup.objects.create(code="chest", name="Грудь")
    back = MuscleGroup.objects.create(code="back", name="Спина")
    barbell = Equipment.objects.create(code="barbell", name="Штанга")
    dumbbell = Equipment.objects.create(code="dumbbell", name="Гантели")

    Exercise.objects.create(
        name="Жим лёжа",
        primary_muscle_group=chest,
        equipment=barbell,
        tracking_type=ExerciseTrackingType.WEIGHT_REPS,
        is_system=True,
    )
    Exercise.objects.create(
        name="Жим гантелей",
        primary_muscle_group=chest,
        equipment=dumbbell,
        tracking_type=ExerciseTrackingType.WEIGHT_REPS,
        is_system=True,
    )
    Exercise.objects.create(
        name="Тяга штанги",
        primary_muscle_group=back,
        equipment=barbell,
        tracking_type=ExerciseTrackingType.WEIGHT_REPS,
        is_system=True,
    )

    client = APIClient()

    response = client.get(
        "/api/v1/exercises",
        {
            "search": "Жим",
            "muscle_group": "chest",
            "equipment": "barbell",
            "tracking_type": ExerciseTrackingType.WEIGHT_REPS,
        },
    )

    body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(body["data"]) == 1
    assert body["data"][0]["name"] == "Жим лёжа"


@pytest.mark.django_db
def test_get_exercise_detail_returns_visible_exercise():
    chest = MuscleGroup.objects.create(code="chest", name="Грудь")
    barbell = Equipment.objects.create(code="barbell", name="Штанга")
    exercise = Exercise.objects.create(
        name="Жим лёжа",
        primary_muscle_group=chest,
        equipment=barbell,
        is_system=True,
    )

    client = APIClient()

    response = client.get(f"/api/v1/exercises/{exercise.id}")

    body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert body["data"]["id"] == str(exercise.id)
    assert body["data"]["name"] == "Жим лёжа"
    assert body["data"]["primary_muscle_group"]["code"] == "chest"


@pytest.mark.django_db
def test_get_exercise_detail_hides_other_user_custom_exercise():
    owner = User.objects.create_user(
        email="owner@example.com",
        password="strong-password-123",
    )
    viewer = User.objects.create_user(
        email="viewer@example.com",
        password="strong-password-123",
    )

    chest = MuscleGroup.objects.create(code="chest", name="Грудь")
    exercise = Exercise.objects.create(
        name="Приватный жим",
        owner=owner,
        primary_muscle_group=chest,
        is_system=False,
    )

    access = str(RefreshToken.for_user(viewer).access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.get(f"/api/v1/exercises/{exercise.id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["error"]["code"] == "NOT_FOUND"

@pytest.mark.django_db
def test_create_custom_exercise_successfully():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    chest = MuscleGroup.objects.create(code="chest", name="Грудь")
    dumbbell = Equipment.objects.create(code="dumbbell", name="Гантели")

    access = str(RefreshToken.for_user(user).access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.post(
        "/api/v1/exercises",
        {
            "name": "Мой жим гантелей",
            "description": "Удобный вариант для домашней тренировки",
            "primary_muscle_group_id": str(chest.id),
            "equipment_id": str(dumbbell.id),
            "tracking_type": ExerciseTrackingType.WEIGHT_REPS,
            "instructions": "Держать лопатки сведёнными",
        },
        format="json",
    )

    body = response.json()

    assert response.status_code == status.HTTP_201_CREATED
    assert body["data"]["name"] == "Мой жим гантелей"
    assert body["data"]["is_system"] is False
    assert body["data"]["owner_id"] == str(user.id)
    assert body["data"]["primary_muscle_group"]["code"] == "chest"
    assert body["data"]["equipment"]["code"] == "dumbbell"

    exercise = Exercise.objects.get(id=body["data"]["id"])

    assert exercise.owner == user
    assert exercise.is_system is False


@pytest.mark.django_db
def test_create_custom_exercise_requires_authentication():
    chest = MuscleGroup.objects.create(code="chest", name="Грудь")

    client = APIClient()

    response = client.post(
        "/api/v1/exercises",
        {
            "name": "Мой жим",
            "primary_muscle_group_id": str(chest.id),
            "tracking_type": ExerciseTrackingType.WEIGHT_REPS,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["error"]["code"] == "NOT_AUTHENTICATED"


@pytest.mark.django_db
def test_create_custom_exercise_rejects_missing_muscle_group():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )

    access = str(RefreshToken.for_user(user).access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.post(
        "/api/v1/exercises",
        {
            "name": "Моё упражнение",
            "primary_muscle_group_id": "00000000-0000-0000-0000-000000000000",
            "tracking_type": ExerciseTrackingType.WEIGHT_REPS,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "primary_muscle_group_id" in response.json()["error"]["fields"]


@pytest.mark.django_db
def test_create_custom_exercise_rejects_inactive_equipment():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    chest = MuscleGroup.objects.create(code="chest", name="Грудь")
    equipment = Equipment.objects.create(
        code="archived",
        name="Архивное",
        is_active=False,
    )

    access = str(RefreshToken.for_user(user).access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.post(
        "/api/v1/exercises",
        {
            "name": "Моё упражнение",
            "primary_muscle_group_id": str(chest.id),
            "equipment_id": str(equipment.id),
            "tracking_type": ExerciseTrackingType.WEIGHT_REPS,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "equipment_id" in response.json()["error"]["fields"]


@pytest.mark.django_db
def test_create_custom_exercise_rejects_invalid_tracking_type():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    chest = MuscleGroup.objects.create(code="chest", name="Грудь")

    access = str(RefreshToken.for_user(user).access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.post(
        "/api/v1/exercises",
        {
            "name": "Моё упражнение",
            "primary_muscle_group_id": str(chest.id),
            "tracking_type": "unknown",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "tracking_type" in response.json()["error"]["fields"]


@pytest.mark.django_db
def test_create_custom_exercise_ignores_owner_and_is_system_from_payload():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    other_user = User.objects.create_user(
        email="other@example.com",
        password="strong-password-123",
    )
    chest = MuscleGroup.objects.create(code="chest", name="Грудь")

    access = str(RefreshToken.for_user(user).access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.post(
        "/api/v1/exercises",
        {
            "name": "Моё упражнение",
            "owner": str(other_user.id),
            "is_system": True,
            "primary_muscle_group_id": str(chest.id),
            "tracking_type": ExerciseTrackingType.WEIGHT_REPS,
        },
        format="json",
    )

    body = response.json()

    assert response.status_code == status.HTTP_201_CREATED
    assert body["data"]["owner_id"] == str(user.id)
    assert body["data"]["is_system"] is False

    exercise = Exercise.objects.get(id=body["data"]["id"])

    assert exercise.owner == user
    assert exercise.is_system is False


@pytest.mark.django_db
def test_patch_custom_exercise_successfully():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    chest = MuscleGroup.objects.create(code="chest", name="Грудь")
    back = MuscleGroup.objects.create(code="back", name="Спина")
    dumbbell = Equipment.objects.create(code="dumbbell", name="Гантели")
    barbell = Equipment.objects.create(code="barbell", name="Штанга")
    exercise = Exercise.objects.create(
        name="Мой жим",
        owner=user,
        primary_muscle_group=chest,
        equipment=dumbbell,
        is_system=False,
    )

    access = str(RefreshToken.for_user(user).access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.patch(
        f"/api/v1/exercises/{exercise.id}",
        {
            "name": "Моя тяга",
            "description": "Обновлённое описание",
            "primary_muscle_group_id": str(back.id),
            "equipment_id": str(barbell.id),
            "tracking_type": ExerciseTrackingType.REPS_ONLY,
            "instructions": "Контролировать движение",
        },
        format="json",
    )

    body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert body["data"]["name"] == "Моя тяга"
    assert body["data"]["description"] == "Обновлённое описание"
    assert body["data"]["primary_muscle_group"]["code"] == "back"
    assert body["data"]["equipment"]["code"] == "barbell"
    assert body["data"]["tracking_type"] == ExerciseTrackingType.REPS_ONLY

    exercise.refresh_from_db()

    assert exercise.owner == user
    assert exercise.is_system is False
    assert exercise.primary_muscle_group == back
    assert exercise.equipment == barbell


@pytest.mark.django_db
def test_patch_custom_exercise_requires_authentication():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    chest = MuscleGroup.objects.create(code="chest", name="Грудь")
    exercise = Exercise.objects.create(
        name="Мой жим",
        owner=user,
        primary_muscle_group=chest,
        is_system=False,
    )

    client = APIClient()

    response = client.patch(
        f"/api/v1/exercises/{exercise.id}",
        {
            "name": "Новое название",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["error"]["code"] == "NOT_AUTHENTICATED"


@pytest.mark.django_db
def test_patch_system_exercise_is_forbidden():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    chest = MuscleGroup.objects.create(code="chest", name="Грудь")
    exercise = Exercise.objects.create(
        name="Жим лёжа",
        primary_muscle_group=chest,
        is_system=True,
    )

    access = str(RefreshToken.for_user(user).access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.patch(
        f"/api/v1/exercises/{exercise.id}",
        {
            "name": "Переименованный жим",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"

    exercise.refresh_from_db()

    assert exercise.name == "Жим лёжа"


@pytest.mark.django_db
def test_patch_other_user_custom_exercise_returns_404():
    owner = User.objects.create_user(
        email="owner@example.com",
        password="strong-password-123",
    )
    viewer = User.objects.create_user(
        email="viewer@example.com",
        password="strong-password-123",
    )
    chest = MuscleGroup.objects.create(code="chest", name="Грудь")
    exercise = Exercise.objects.create(
        name="Чужой жим",
        owner=owner,
        primary_muscle_group=chest,
        is_system=False,
    )

    access = str(RefreshToken.for_user(viewer).access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.patch(
        f"/api/v1/exercises/{exercise.id}",
        {
            "name": "Попытка изменения",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["error"]["code"] == "NOT_FOUND"

    exercise.refresh_from_db()

    assert exercise.name == "Чужой жим"


@pytest.mark.django_db
def test_patch_custom_exercise_rejects_inactive_muscle_group():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    chest = MuscleGroup.objects.create(code="chest", name="Грудь")
    archived = MuscleGroup.objects.create(
        code="archived",
        name="Архивная группа",
        is_active=False,
    )
    exercise = Exercise.objects.create(
        name="Мой жим",
        owner=user,
        primary_muscle_group=chest,
        is_system=False,
    )

    access = str(RefreshToken.for_user(user).access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.patch(
        f"/api/v1/exercises/{exercise.id}",
        {
            "primary_muscle_group_id": str(archived.id),
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "primary_muscle_group_id" in response.json()["error"]["fields"]


@pytest.mark.django_db
def test_delete_custom_exercise_archives_it():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    chest = MuscleGroup.objects.create(code="chest", name="Грудь")
    exercise = Exercise.objects.create(
        name="Мой жим",
        owner=user,
        primary_muscle_group=chest,
        is_system=False,
    )

    access = str(RefreshToken.for_user(user).access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.delete(f"/api/v1/exercises/{exercise.id}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["data"]["success"] is True

    exercise.refresh_from_db()

    assert exercise.is_active is False

    list_response = client.get("/api/v1/exercises")

    assert all(
        item["id"] != str(exercise.id)
        for item in list_response.json()["data"]
    )


@pytest.mark.django_db
def test_delete_system_exercise_is_forbidden():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    chest = MuscleGroup.objects.create(code="chest", name="Грудь")
    exercise = Exercise.objects.create(
        name="Жим лёжа",
        primary_muscle_group=chest,
        is_system=True,
    )

    access = str(RefreshToken.for_user(user).access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.delete(f"/api/v1/exercises/{exercise.id}")

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"

    exercise.refresh_from_db()

    assert exercise.is_active is True


@pytest.mark.django_db
def test_delete_other_user_custom_exercise_returns_404():
    owner = User.objects.create_user(
        email="owner@example.com",
        password="strong-password-123",
    )
    viewer = User.objects.create_user(
        email="viewer@example.com",
        password="strong-password-123",
    )
    chest = MuscleGroup.objects.create(code="chest", name="Грудь")
    exercise = Exercise.objects.create(
        name="Чужой жим",
        owner=owner,
        primary_muscle_group=chest,
        is_system=False,
    )

    access = str(RefreshToken.for_user(viewer).access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.delete(f"/api/v1/exercises/{exercise.id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["error"]["code"] == "NOT_FOUND"

    exercise.refresh_from_db()

    assert exercise.is_active is True
