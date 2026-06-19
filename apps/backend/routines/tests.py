import pytest
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User
from exercises.models import Equipment, Exercise, ExerciseTrackingType, MuscleGroup
from routines.models import Routine, RoutineDay, RoutineExercise


@pytest.mark.django_db
def test_get_routines_requires_authentication():
    client = APIClient()

    response = client.get("/api/v1/routines")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["error"]["code"] == "NOT_AUTHENTICATED"


@pytest.mark.django_db
def test_get_routines_returns_only_current_user_routines():
    first_user = User.objects.create_user(
        email="first@example.com",
        password="strong-password-123",
    )
    second_user = User.objects.create_user(
        email="second@example.com",
        password="strong-password-123",
    )
    first_routine = Routine.objects.create(
        user=first_user,
        name="Full Body A",
    )
    Routine.objects.create(
        user=second_user,
        name="Other Routine",
    )

    access = str(RefreshToken.for_user(first_user).access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.get("/api/v1/routines")

    body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(body["data"]) == 1
    assert body["data"][0]["id"] == str(first_routine.id)
    assert body["data"][0]["name"] == "Full Body A"


@pytest.mark.django_db
def test_get_routines_excludes_deleted_routines():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    Routine.objects.create(
        user=user,
        name="Visible Routine",
    )
    Routine.objects.create(
        user=user,
        name="Deleted Routine",
        deleted_at="2026-06-18T00:00:00Z",
    )

    access = str(RefreshToken.for_user(user).access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.get("/api/v1/routines")

    names = [item["name"] for item in response.json()["data"]]

    assert response.status_code == status.HTTP_200_OK
    assert names == ["Visible Routine"]


@pytest.mark.django_db
def test_get_routines_supports_limit_offset_pagination():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    Routine.objects.create(user=user, name="A")
    second = Routine.objects.create(user=user, name="B")
    Routine.objects.create(user=user, name="C")

    access = str(RefreshToken.for_user(user).access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.get("/api/v1/routines?limit=1&offset=1")

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
def test_create_routine_successfully():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    access = str(RefreshToken.for_user(user).access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.post(
        "/api/v1/routines",
        {
            "name": "Full Body A",
            "description": "Три тренировки в неделю",
            "color": "#22c55e",
        },
        format="json",
    )

    body = response.json()

    assert response.status_code == status.HTTP_201_CREATED
    assert body["data"]["name"] == "Full Body A"
    assert body["data"]["description"] == "Три тренировки в неделю"
    assert body["data"]["color"] == "#22c55e"
    assert body["data"]["is_active"] is True
    assert body["data"]["version"] == 1
    assert body["data"]["days"] == []

    routine = Routine.objects.get(id=body["data"]["id"])

    assert routine.user == user


@pytest.mark.django_db
def test_create_routine_requires_authentication():
    client = APIClient()

    response = client.post(
        "/api/v1/routines",
        {
            "name": "Full Body A",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["error"]["code"] == "NOT_AUTHENTICATED"


@pytest.mark.django_db
def test_create_routine_requires_name():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    access = str(RefreshToken.for_user(user).access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.post(
        "/api/v1/routines",
        {
            "description": "Без названия нельзя",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "name" in response.json()["error"]["fields"]


@pytest.mark.django_db
def test_get_routine_detail_returns_current_user_routine():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    routine = Routine.objects.create(
        user=user,
        name="Full Body A",
        description="Описание",
    )

    access = str(RefreshToken.for_user(user).access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.get(f"/api/v1/routines/{routine.id}")

    body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert body["data"]["id"] == str(routine.id)
    assert body["data"]["name"] == "Full Body A"
    assert body["data"]["description"] == "Описание"


@pytest.mark.django_db
def test_get_routine_detail_returns_404_for_other_user_routine():
    first_user = User.objects.create_user(
        email="first@example.com",
        password="strong-password-123",
    )
    second_user = User.objects.create_user(
        email="second@example.com",
        password="strong-password-123",
    )
    routine = Routine.objects.create(
        user=second_user,
        name="Other Routine",
    )

    access = str(RefreshToken.for_user(first_user).access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.get(f"/api/v1/routines/{routine.id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.django_db
def test_patch_routine_updates_current_user_routine_and_increments_version():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    routine = Routine.objects.create(
        user=user,
        name="Old Name",
        description="Old description",
        color="#111111",
    )

    access = str(RefreshToken.for_user(user).access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.patch(
        f"/api/v1/routines/{routine.id}",
        {
            "name": "New Name",
            "description": "New description",
            "color": "#22c55e",
        },
        format="json",
    )

    body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert body["data"]["name"] == "New Name"
    assert body["data"]["description"] == "New description"
    assert body["data"]["color"] == "#22c55e"
    assert body["data"]["version"] == 2

    routine.refresh_from_db()

    assert routine.name == "New Name"
    assert routine.version == 2


@pytest.mark.django_db
def test_patch_routine_requires_authentication():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    routine = Routine.objects.create(
        user=user,
        name="Full Body A",
    )

    client = APIClient()

    response = client.patch(
        f"/api/v1/routines/{routine.id}",
        {
            "name": "New Name",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["error"]["code"] == "NOT_AUTHENTICATED"


@pytest.mark.django_db
def test_patch_routine_returns_404_for_other_user_routine():
    first_user = User.objects.create_user(
        email="first@example.com",
        password="strong-password-123",
    )
    second_user = User.objects.create_user(
        email="second@example.com",
        password="strong-password-123",
    )
    routine = Routine.objects.create(
        user=second_user,
        name="Other Routine",
    )

    access = str(RefreshToken.for_user(first_user).access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.patch(
        f"/api/v1/routines/{routine.id}",
        {
            "name": "Hijacked",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["error"]["code"] == "NOT_FOUND"

    routine.refresh_from_db()

    assert routine.name == "Other Routine"


@pytest.mark.django_db
def test_patch_routine_rejects_blank_name():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    routine = Routine.objects.create(
        user=user,
        name="Full Body A",
    )

    access = str(RefreshToken.for_user(user).access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.patch(
        f"/api/v1/routines/{routine.id}",
        {
            "name": "",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "name" in response.json()["error"]["fields"]


@pytest.mark.django_db
def test_delete_routine_soft_deletes_current_user_routine():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    routine = Routine.objects.create(
        user=user,
        name="Full Body A",
    )

    access = str(RefreshToken.for_user(user).access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.delete(f"/api/v1/routines/{routine.id}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["data"]["success"] is True

    routine.refresh_from_db()

    assert routine.deleted_at is not None
    assert routine.is_active is False
    assert routine.version == 2

    list_response = client.get("/api/v1/routines")

    assert list_response.json()["data"] == []


@pytest.mark.django_db
def test_delete_routine_returns_404_for_other_user_routine():
    first_user = User.objects.create_user(
        email="first@example.com",
        password="strong-password-123",
    )
    second_user = User.objects.create_user(
        email="second@example.com",
        password="strong-password-123",
    )
    routine = Routine.objects.create(
        user=second_user,
        name="Other Routine",
    )

    access = str(RefreshToken.for_user(first_user).access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.delete(f"/api/v1/routines/{routine.id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["error"]["code"] == "NOT_FOUND"

    routine.refresh_from_db()

    assert routine.deleted_at is None
    assert routine.is_active is True


@pytest.mark.django_db
def test_create_routine_day_successfully():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    routine = Routine.objects.create(
        user=user,
        name="Full Body A",
    )
    access = str(RefreshToken.for_user(user).access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.post(
        f"/api/v1/routines/{routine.id}/days",
        {
            "name": "День A",
            "position": 1,
            "planned_weekday": 1,
        },
        format="json",
    )

    body = response.json()

    assert response.status_code == status.HTTP_201_CREATED
    assert body["data"]["name"] == "День A"
    assert body["data"]["position"] == 1
    assert body["data"]["planned_weekday"] == 1
    assert body["data"]["exercises"] == []

    routine_day = RoutineDay.objects.get(id=body["data"]["id"])

    assert routine_day.routine == routine

    routine.refresh_from_db()

    assert routine.version == 2


@pytest.mark.django_db
def test_create_routine_day_requires_authentication():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    routine = Routine.objects.create(
        user=user,
        name="Full Body A",
    )

    client = APIClient()

    response = client.post(
        f"/api/v1/routines/{routine.id}/days",
        {
            "name": "День A",
            "position": 1,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["error"]["code"] == "NOT_AUTHENTICATED"


@pytest.mark.django_db
def test_create_routine_day_returns_404_for_other_user_routine():
    first_user = User.objects.create_user(
        email="first@example.com",
        password="strong-password-123",
    )
    second_user = User.objects.create_user(
        email="second@example.com",
        password="strong-password-123",
    )
    routine = Routine.objects.create(
        user=second_user,
        name="Other Routine",
    )
    access = str(RefreshToken.for_user(first_user).access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.post(
        f"/api/v1/routines/{routine.id}/days",
        {
            "name": "День A",
            "position": 1,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["error"]["code"] == "NOT_FOUND"
    assert RoutineDay.objects.count() == 0


@pytest.mark.django_db
def test_create_routine_day_rejects_duplicate_position():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    routine = Routine.objects.create(
        user=user,
        name="Full Body A",
    )
    RoutineDay.objects.create(
        routine=routine,
        name="День A",
        position=1,
    )
    access = str(RefreshToken.for_user(user).access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.post(
        f"/api/v1/routines/{routine.id}/days",
        {
            "name": "День B",
            "position": 1,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "position" in response.json()["error"]["fields"]


@pytest.mark.django_db
def test_patch_routine_day_updates_current_user_day():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    routine = Routine.objects.create(
        user=user,
        name="Full Body A",
    )
    routine_day = RoutineDay.objects.create(
        routine=routine,
        name="День A",
        position=1,
    )
    access = str(RefreshToken.for_user(user).access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.patch(
        f"/api/v1/routine-days/{routine_day.id}",
        {
            "name": "День B",
            "position": 2,
            "planned_weekday": 3,
        },
        format="json",
    )

    body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert body["data"]["name"] == "День B"
    assert body["data"]["position"] == 2
    assert body["data"]["planned_weekday"] == 3

    routine_day.refresh_from_db()
    routine.refresh_from_db()

    assert routine_day.name == "День B"
    assert routine.version == 2


@pytest.mark.django_db
def test_patch_routine_day_returns_404_for_other_user_day():
    first_user = User.objects.create_user(
        email="first@example.com",
        password="strong-password-123",
    )
    second_user = User.objects.create_user(
        email="second@example.com",
        password="strong-password-123",
    )
    routine = Routine.objects.create(
        user=second_user,
        name="Other Routine",
    )
    routine_day = RoutineDay.objects.create(
        routine=routine,
        name="Other Day",
        position=1,
    )
    access = str(RefreshToken.for_user(first_user).access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.patch(
        f"/api/v1/routine-days/{routine_day.id}",
        {
            "name": "Hijacked",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["error"]["code"] == "NOT_FOUND"

    routine_day.refresh_from_db()

    assert routine_day.name == "Other Day"


@pytest.mark.django_db
def test_delete_routine_day_removes_current_user_day():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    routine = Routine.objects.create(
        user=user,
        name="Full Body A",
    )
    routine_day = RoutineDay.objects.create(
        routine=routine,
        name="День A",
        position=1,
    )
    access = str(RefreshToken.for_user(user).access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.delete(f"/api/v1/routine-days/{routine_day.id}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["data"]["success"] is True
    assert not RoutineDay.objects.filter(id=routine_day.id).exists()

    routine.refresh_from_db()

    assert routine.version == 2


@pytest.mark.django_db
def test_delete_routine_day_returns_404_for_other_user_day():
    first_user = User.objects.create_user(
        email="first@example.com",
        password="strong-password-123",
    )
    second_user = User.objects.create_user(
        email="second@example.com",
        password="strong-password-123",
    )
    routine = Routine.objects.create(
        user=second_user,
        name="Other Routine",
    )
    routine_day = RoutineDay.objects.create(
        routine=routine,
        name="Other Day",
        position=1,
    )
    access = str(RefreshToken.for_user(first_user).access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.delete(f"/api/v1/routine-days/{routine_day.id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["error"]["code"] == "NOT_FOUND"
    assert RoutineDay.objects.filter(id=routine_day.id).exists()


@pytest.mark.django_db
def test_create_routine_exercise_successfully():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    routine = Routine.objects.create(user=user, name="Full Body A")
    routine_day = RoutineDay.objects.create(
        routine=routine,
        name="День A",
        position=1,
    )
    chest = MuscleGroup.objects.create(code="chest", name="Грудь")
    barbell = Equipment.objects.create(code="barbell", name="Штанга")
    exercise = Exercise.objects.create(
        name="Жим лёжа",
        primary_muscle_group=chest,
        equipment=barbell,
        tracking_type=ExerciseTrackingType.WEIGHT_REPS,
        is_system=True,
    )
    access = str(RefreshToken.for_user(user).access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.post(
        f"/api/v1/routine-days/{routine_day.id}/exercises",
        {
            "exercise_id": str(exercise.id),
            "position": 1,
            "planned_sets": 4,
            "rep_min": 6,
            "rep_max": 8,
            "target_weight": "80.00",
            "target_rpe": "8.50",
            "target_rir": "2.00",
            "rest_seconds": 120,
            "notes": "Рабочие подходы",
            "superset_group": "A",
        },
        format="json",
    )

    body = response.json()

    assert response.status_code == status.HTTP_201_CREATED
    assert body["data"]["exercise_id"] == str(exercise.id)
    assert body["data"]["position"] == 1
    assert body["data"]["planned_sets"] == 4
    assert body["data"]["rep_min"] == 6
    assert body["data"]["rep_max"] == 8
    assert body["data"]["target_weight"] == "80.00"
    assert body["data"]["target_rpe"] == "8.50"
    assert body["data"]["target_rir"] == "2.00"

    routine_exercise = RoutineExercise.objects.get(id=body["data"]["id"])

    assert routine_exercise.routine_day == routine_day
    assert routine_exercise.exercise == exercise

    routine.refresh_from_db()

    assert routine.version == 2


@pytest.mark.django_db
def test_create_routine_exercise_requires_authentication():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    routine = Routine.objects.create(user=user, name="Full Body A")
    routine_day = RoutineDay.objects.create(
        routine=routine,
        name="День A",
        position=1,
    )

    client = APIClient()

    response = client.post(
        f"/api/v1/routine-days/{routine_day.id}/exercises",
        {
            "exercise_id": "00000000-0000-0000-0000-000000000000",
            "position": 1,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["error"]["code"] == "NOT_AUTHENTICATED"


@pytest.mark.django_db
def test_create_routine_exercise_returns_404_for_other_user_day():
    first_user = User.objects.create_user(
        email="first@example.com",
        password="strong-password-123",
    )
    second_user = User.objects.create_user(
        email="second@example.com",
        password="strong-password-123",
    )
    routine = Routine.objects.create(user=second_user, name="Other Routine")
    routine_day = RoutineDay.objects.create(
        routine=routine,
        name="Other Day",
        position=1,
    )
    access = str(RefreshToken.for_user(first_user).access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.post(
        f"/api/v1/routine-days/{routine_day.id}/exercises",
        {
            "exercise_id": "00000000-0000-0000-0000-000000000000",
            "position": 1,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.django_db
def test_create_routine_exercise_rejects_other_user_custom_exercise():
    owner = User.objects.create_user(
        email="owner@example.com",
        password="strong-password-123",
    )
    viewer = User.objects.create_user(
        email="viewer@example.com",
        password="strong-password-123",
    )
    routine = Routine.objects.create(user=viewer, name="Full Body A")
    routine_day = RoutineDay.objects.create(
        routine=routine,
        name="День A",
        position=1,
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

    response = client.post(
        f"/api/v1/routine-days/{routine_day.id}/exercises",
        {
            "exercise_id": str(exercise.id),
            "position": 1,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "exercise_id" in response.json()["error"]["fields"]


@pytest.mark.django_db
def test_create_routine_exercise_rejects_duplicate_position():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    routine = Routine.objects.create(user=user, name="Full Body A")
    routine_day = RoutineDay.objects.create(
        routine=routine,
        name="День A",
        position=1,
    )
    chest = MuscleGroup.objects.create(code="chest", name="Грудь")
    exercise = Exercise.objects.create(
        name="Жим лёжа",
        primary_muscle_group=chest,
        is_system=True,
    )
    RoutineExercise.objects.create(
        routine_day=routine_day,
        exercise=exercise,
        position=1,
    )
    access = str(RefreshToken.for_user(user).access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.post(
        f"/api/v1/routine-days/{routine_day.id}/exercises",
        {
            "exercise_id": str(exercise.id),
            "position": 1,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "position" in response.json()["error"]["fields"]


@pytest.mark.django_db
def test_create_routine_exercise_rejects_invalid_rep_range():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    routine = Routine.objects.create(user=user, name="Full Body A")
    routine_day = RoutineDay.objects.create(
        routine=routine,
        name="День A",
        position=1,
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

    response = client.post(
        f"/api/v1/routine-days/{routine_day.id}/exercises",
        {
            "exercise_id": str(exercise.id),
            "position": 1,
            "rep_min": 10,
            "rep_max": 8,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "rep_min" in response.json()["error"]["fields"]


@pytest.mark.django_db
def test_patch_routine_exercise_updates_current_user_item():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    routine = Routine.objects.create(user=user, name="Full Body A")
    routine_day = RoutineDay.objects.create(
        routine=routine,
        name="День A",
        position=1,
    )
    chest = MuscleGroup.objects.create(code="chest", name="Грудь")
    back = MuscleGroup.objects.create(code="back", name="Спина")
    first_exercise = Exercise.objects.create(
        name="Жим лёжа",
        primary_muscle_group=chest,
        is_system=True,
    )
    second_exercise = Exercise.objects.create(
        name="Тяга",
        primary_muscle_group=back,
        is_system=True,
    )
    routine_exercise = RoutineExercise.objects.create(
        routine_day=routine_day,
        exercise=first_exercise,
        position=1,
        planned_sets=3,
    )
    access = str(RefreshToken.for_user(user).access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.patch(
        f"/api/v1/routine-exercises/{routine_exercise.id}",
        {
            "exercise_id": str(second_exercise.id),
            "position": 2,
            "planned_sets": 5,
            "rep_min": 8,
            "rep_max": 12,
            "rest_seconds": 90,
        },
        format="json",
    )

    body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert body["data"]["exercise_id"] == str(second_exercise.id)
    assert body["data"]["position"] == 2
    assert body["data"]["planned_sets"] == 5
    assert body["data"]["rep_min"] == 8
    assert body["data"]["rep_max"] == 12
    assert body["data"]["rest_seconds"] == 90

    routine_exercise.refresh_from_db()
    routine.refresh_from_db()

    assert routine_exercise.exercise == second_exercise
    assert routine.version == 2


@pytest.mark.django_db
def test_patch_routine_exercise_returns_404_for_other_user_item():
    first_user = User.objects.create_user(
        email="first@example.com",
        password="strong-password-123",
    )
    second_user = User.objects.create_user(
        email="second@example.com",
        password="strong-password-123",
    )
    routine = Routine.objects.create(user=second_user, name="Other Routine")
    routine_day = RoutineDay.objects.create(
        routine=routine,
        name="Other Day",
        position=1,
    )
    chest = MuscleGroup.objects.create(code="chest", name="Грудь")
    exercise = Exercise.objects.create(
        name="Жим лёжа",
        primary_muscle_group=chest,
        is_system=True,
    )
    routine_exercise = RoutineExercise.objects.create(
        routine_day=routine_day,
        exercise=exercise,
        position=1,
    )
    access = str(RefreshToken.for_user(first_user).access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.patch(
        f"/api/v1/routine-exercises/{routine_exercise.id}",
        {
            "position": 2,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.django_db
def test_patch_routine_exercise_rejects_partial_invalid_rep_range():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    routine = Routine.objects.create(user=user, name="Full Body A")
    routine_day = RoutineDay.objects.create(
        routine=routine,
        name="День A",
        position=1,
    )
    chest = MuscleGroup.objects.create(code="chest", name="Грудь")
    exercise = Exercise.objects.create(
        name="Жим лёжа",
        primary_muscle_group=chest,
        is_system=True,
    )
    routine_exercise = RoutineExercise.objects.create(
        routine_day=routine_day,
        exercise=exercise,
        position=1,
        rep_min=10,
        rep_max=12,
    )
    access = str(RefreshToken.for_user(user).access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.patch(
        f"/api/v1/routine-exercises/{routine_exercise.id}",
        {
            "rep_max": 8,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "rep_min" in response.json()["error"]["fields"]


@pytest.mark.django_db
def test_delete_routine_exercise_removes_current_user_item():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    routine = Routine.objects.create(user=user, name="Full Body A")
    routine_day = RoutineDay.objects.create(
        routine=routine,
        name="День A",
        position=1,
    )
    chest = MuscleGroup.objects.create(code="chest", name="Грудь")
    exercise = Exercise.objects.create(
        name="Жим лёжа",
        primary_muscle_group=chest,
        is_system=True,
    )
    routine_exercise = RoutineExercise.objects.create(
        routine_day=routine_day,
        exercise=exercise,
        position=1,
    )
    access = str(RefreshToken.for_user(user).access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.delete(f"/api/v1/routine-exercises/{routine_exercise.id}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["data"]["success"] is True
    assert not RoutineExercise.objects.filter(id=routine_exercise.id).exists()

    routine.refresh_from_db()

    assert routine.version == 2


@pytest.mark.django_db
def test_delete_routine_exercise_returns_404_for_other_user_item():
    first_user = User.objects.create_user(
        email="first@example.com",
        password="strong-password-123",
    )
    second_user = User.objects.create_user(
        email="second@example.com",
        password="strong-password-123",
    )
    routine = Routine.objects.create(user=second_user, name="Other Routine")
    routine_day = RoutineDay.objects.create(
        routine=routine,
        name="Other Day",
        position=1,
    )
    chest = MuscleGroup.objects.create(code="chest", name="Грудь")
    exercise = Exercise.objects.create(
        name="Жим лёжа",
        primary_muscle_group=chest,
        is_system=True,
    )
    routine_exercise = RoutineExercise.objects.create(
        routine_day=routine_day,
        exercise=exercise,
        position=1,
    )
    access = str(RefreshToken.for_user(first_user).access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.delete(f"/api/v1/routine-exercises/{routine_exercise.id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["error"]["code"] == "NOT_FOUND"
    assert RoutineExercise.objects.filter(id=routine_exercise.id).exists()
