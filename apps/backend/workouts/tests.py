from datetime import datetime, timezone

import pytest
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User
from exercises.models import Equipment, Exercise, ExerciseTrackingType, MuscleGroup
from routines.models import Routine, RoutineDay, RoutineExercise
from workouts.models import (
    PersonalRecord,
    PersonalRecordType,
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
def test_start_empty_workout_successfully():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    client = authenticate_client(user)

    response = client.post(
        "/api/v1/workouts",
        {
            "name": "Свободная тренировка",
            "started_at": "2026-06-18T10:00:00Z",
            "notes": "Без программы",
        },
        format="json",
    )

    body = response.json()

    assert response.status_code == status.HTTP_201_CREATED
    assert body["data"]["name"] == "Свободная тренировка"
    assert body["data"]["status"] == WorkoutStatus.ACTIVE
    assert body["data"]["notes"] == "Без программы"
    assert body["data"]["source_routine_id"] is None
    assert body["data"]["source_routine_day_id"] is None
    assert body["data"]["exercises"] == []

    workout = Workout.objects.get(id=body["data"]["id"])

    assert workout.user == user
    assert workout.started_at == datetime(2026, 6, 18, 10, 0, tzinfo=timezone.utc)


@pytest.mark.django_db
def test_start_workout_is_idempotent_by_local_device_id():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    client = authenticate_client(user)
    payload = {
        "name": "Свободная тренировка",
        "started_at": "2026-06-18T10:00:00Z",
        "local_device_id": "00000000-0000-0000-0000-000000000001",
        "client_updated_at": "2026-06-18T10:00:05Z",
    }

    first_response = client.post("/api/v1/workouts", payload, format="json")
    second_response = client.post("/api/v1/workouts", payload, format="json")

    assert first_response.status_code == status.HTTP_201_CREATED
    assert second_response.status_code == status.HTTP_201_CREATED
    assert second_response.json()["data"]["id"] == first_response.json()["data"]["id"]
    assert Workout.objects.filter(user=user).count() == 1


@pytest.mark.django_db
def test_start_workout_local_device_id_is_scoped_to_user():
    first_user = User.objects.create_user(
        email="first@example.com",
        password="strong-password-123",
    )
    second_user = User.objects.create_user(
        email="second@example.com",
        password="strong-password-123",
    )
    payload = {
        "name": "Свободная тренировка",
        "local_device_id": "00000000-0000-0000-0000-000000000001",
    }

    first_response = authenticate_client(first_user).post(
        "/api/v1/workouts",
        payload,
        format="json",
    )
    second_response = authenticate_client(second_user).post(
        "/api/v1/workouts",
        payload,
        format="json",
    )

    assert first_response.status_code == status.HTTP_201_CREATED
    assert second_response.status_code == status.HTTP_201_CREATED
    assert first_response.json()["data"]["id"] != second_response.json()["data"]["id"]
    assert Workout.objects.count() == 2


@pytest.mark.django_db
def test_start_workout_from_routine_day_copies_template():
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
    routine_exercise = RoutineExercise.objects.create(
        routine_day=routine_day,
        exercise=exercise,
        position=1,
        planned_sets=3,
        rep_min=6,
        rep_max=8,
        target_weight="80.00",
        target_rpe="8.00",
        target_rir="2.00",
        notes="Жимовая база",
        superset_group="A",
    )
    client = authenticate_client(user)

    response = client.post(
        "/api/v1/workouts",
        {
            "source_routine_day_id": str(routine_day.id),
        },
        format="json",
    )

    body = response.json()

    assert response.status_code == status.HTTP_201_CREATED
    assert body["data"]["name"] == "День A"
    assert body["data"]["source_routine_id"] == str(routine.id)
    assert body["data"]["source_routine_day_id"] == str(routine_day.id)
    assert len(body["data"]["exercises"]) == 1

    workout_exercise_data = body["data"]["exercises"][0]

    assert workout_exercise_data["exercise_id"] == str(exercise.id)
    assert workout_exercise_data["source_routine_exercise_id"] == str(routine_exercise.id)
    assert workout_exercise_data["position"] == 1
    assert workout_exercise_data["notes"] == "Жимовая база"
    assert workout_exercise_data["superset_group"] == "A"
    assert len(workout_exercise_data["sets"]) == 3
    assert [item["position"] for item in workout_exercise_data["sets"]] == [1, 2, 3]
    assert all(item["set_type"] == "working" for item in workout_exercise_data["sets"])
    assert all(item["weight"] == "80.00" for item in workout_exercise_data["sets"])
    assert all(item["repetitions"] == 6 for item in workout_exercise_data["sets"])
    assert all(item["rpe"] == "8.00" for item in workout_exercise_data["sets"])
    assert all(item["rir"] == "2.00" for item in workout_exercise_data["sets"])
    assert all(item["is_completed"] is False for item in workout_exercise_data["sets"])

    workout = Workout.objects.get(id=body["data"]["id"])

    assert workout.exercises.count() == 1
    assert WorkoutExercise.objects.get(workout=workout).sets.count() == 3


@pytest.mark.django_db
def test_start_workout_requires_authentication():
    client = APIClient()

    response = client.post(
        "/api/v1/workouts",
        {
            "name": "Свободная тренировка",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["error"]["code"] == "NOT_AUTHENTICATED"


@pytest.mark.django_db
def test_start_workout_returns_404_for_other_user_routine_day():
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
    client = authenticate_client(first_user)

    response = client.post(
        "/api/v1/workouts",
        {
            "source_routine_day_id": str(routine_day.id),
        },
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["error"]["code"] == "NOT_FOUND"
    assert Workout.objects.count() == 0


@pytest.mark.django_db
def test_start_workout_returns_404_for_deleted_routine():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    routine = Routine.objects.create(
        user=user,
        name="Deleted Routine",
        deleted_at="2026-06-18T00:00:00Z",
    )
    routine_day = RoutineDay.objects.create(
        routine=routine,
        name="Deleted Day",
        position=1,
    )
    client = authenticate_client(user)

    response = client.post(
        "/api/v1/workouts",
        {
            "source_routine_day_id": str(routine_day.id),
        },
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["error"]["code"] == "NOT_FOUND"
    assert Workout.objects.count() == 0


@pytest.mark.django_db
def test_started_workout_is_independent_from_later_routine_changes():
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
        planned_sets=2,
        rep_min=5,
        target_weight="70.00",
    )
    client = authenticate_client(user)

    response = client.post(
        "/api/v1/workouts",
        {
            "source_routine_day_id": str(routine_day.id),
        },
        format="json",
    )

    workout_id = response.json()["data"]["id"]

    routine_exercise.planned_sets = 5
    routine_exercise.rep_min = 10
    routine_exercise.target_weight = "100.00"
    routine_exercise.save()

    workout_exercise = WorkoutExercise.objects.get(workout_id=workout_id)
    sets = list(WorkoutSet.objects.filter(workout_exercise=workout_exercise))

    assert len(sets) == 2
    assert all(item.repetitions == 5 for item in sets)
    assert all(str(item.weight) == "70.00" for item in sets)


@pytest.mark.django_db
def test_get_active_workout_requires_authentication():
    client = APIClient()

    response = client.get("/api/v1/workouts/active")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["error"]["code"] == "NOT_AUTHENTICATED"


@pytest.mark.django_db
def test_get_active_workout_returns_null_when_missing():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    client = authenticate_client(user)

    response = client.get("/api/v1/workouts/active")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "data": None,
        "meta": {},
    }


@pytest.mark.django_db
def test_get_active_workout_returns_latest_active_workout():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    older = Workout.objects.create(
        user=user,
        name="Старая активная",
        started_at=datetime(2026, 6, 18, 8, 0, tzinfo=timezone.utc),
        status=WorkoutStatus.ACTIVE,
    )
    latest = Workout.objects.create(
        user=user,
        name="Новая активная",
        started_at=datetime(2026, 6, 18, 10, 0, tzinfo=timezone.utc),
        status=WorkoutStatus.ACTIVE,
    )
    chest = MuscleGroup.objects.create(code="chest", name="Грудь")
    exercise = Exercise.objects.create(
        name="Жим лёжа",
        primary_muscle_group=chest,
        is_system=True,
    )
    workout_exercise = WorkoutExercise.objects.create(
        workout=latest,
        exercise=exercise,
        position=1,
    )
    WorkoutSet.objects.create(
        workout_exercise=workout_exercise,
        position=1,
        repetitions=8,
    )
    client = authenticate_client(user)

    response = client.get("/api/v1/workouts/active")

    body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert body["data"]["id"] == str(latest.id)
    assert body["data"]["name"] == "Новая активная"
    assert body["data"]["id"] != str(older.id)
    assert len(body["data"]["exercises"]) == 1
    assert len(body["data"]["exercises"][0]["sets"]) == 1


@pytest.mark.django_db
def test_get_active_workout_ignores_non_active_deleted_and_other_user_workouts():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    other_user = User.objects.create_user(
        email="other@example.com",
        password="strong-password-123",
    )
    Workout.objects.create(
        user=user,
        name="Завершённая",
        started_at=datetime(2026, 6, 18, 8, 0, tzinfo=timezone.utc),
        status=WorkoutStatus.COMPLETED,
    )
    Workout.objects.create(
        user=user,
        name="Удалённая активная",
        started_at=datetime(2026, 6, 18, 9, 0, tzinfo=timezone.utc),
        status=WorkoutStatus.ACTIVE,
        deleted_at=datetime(2026, 6, 18, 9, 30, tzinfo=timezone.utc),
    )
    Workout.objects.create(
        user=other_user,
        name="Чужая активная",
        started_at=datetime(2026, 6, 18, 10, 0, tzinfo=timezone.utc),
        status=WorkoutStatus.ACTIVE,
    )
    client = authenticate_client(user)

    response = client.get("/api/v1/workouts/active")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["data"] is None


@pytest.mark.django_db
def test_create_workout_set_successfully():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    workout = Workout.objects.create(
        user=user,
        name="Тренировка",
        started_at=datetime(2026, 6, 18, 10, 0, tzinfo=timezone.utc),
    )
    chest = MuscleGroup.objects.create(code="chest", name="Грудь")
    exercise = Exercise.objects.create(
        name="Жим лёжа",
        primary_muscle_group=chest,
        is_system=True,
    )
    workout_exercise = WorkoutExercise.objects.create(
        workout=workout,
        exercise=exercise,
        position=1,
    )
    client = authenticate_client(user)

    response = client.post(
        f"/api/v1/workout-exercises/{workout_exercise.id}/sets",
        {
            "position": 1,
            "set_type": WorkoutSetType.WORKING,
            "weight": "80.00",
            "repetitions": 8,
            "rpe": "8.50",
            "rir": "2.00",
            "is_completed": True,
            "notes": "Хороший подход",
        },
        format="json",
    )

    body = response.json()

    assert response.status_code == status.HTTP_201_CREATED
    assert body["data"]["position"] == 1
    assert body["data"]["set_type"] == WorkoutSetType.WORKING
    assert body["data"]["weight"] == "80.00"
    assert body["data"]["repetitions"] == 8
    assert body["data"]["rpe"] == "8.50"
    assert body["data"]["rir"] == "2.00"
    assert body["data"]["is_completed"] is True
    assert body["data"]["completed_at"] is not None

    workout_set = WorkoutSet.objects.get(id=body["data"]["id"])

    assert workout_set.workout_exercise == workout_exercise

    workout.refresh_from_db()

    assert workout.server_version == 2


@pytest.mark.django_db
def test_create_workout_set_requires_authentication():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    workout = Workout.objects.create(
        user=user,
        name="Тренировка",
        started_at=datetime(2026, 6, 18, 10, 0, tzinfo=timezone.utc),
    )
    chest = MuscleGroup.objects.create(code="chest", name="Грудь")
    exercise = Exercise.objects.create(
        name="Жим лёжа",
        primary_muscle_group=chest,
        is_system=True,
    )
    workout_exercise = WorkoutExercise.objects.create(
        workout=workout,
        exercise=exercise,
        position=1,
    )
    client = APIClient()

    response = client.post(
        f"/api/v1/workout-exercises/{workout_exercise.id}/sets",
        {
            "position": 1,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["error"]["code"] == "NOT_AUTHENTICATED"


@pytest.mark.django_db
def test_create_workout_set_returns_404_for_other_user_workout_exercise():
    owner = User.objects.create_user(
        email="owner@example.com",
        password="strong-password-123",
    )
    viewer = User.objects.create_user(
        email="viewer@example.com",
        password="strong-password-123",
    )
    workout = Workout.objects.create(
        user=owner,
        name="Тренировка",
        started_at=datetime(2026, 6, 18, 10, 0, tzinfo=timezone.utc),
    )
    chest = MuscleGroup.objects.create(code="chest", name="Грудь")
    exercise = Exercise.objects.create(
        name="Жим лёжа",
        primary_muscle_group=chest,
        is_system=True,
    )
    workout_exercise = WorkoutExercise.objects.create(
        workout=workout,
        exercise=exercise,
        position=1,
    )
    client = authenticate_client(viewer)

    response = client.post(
        f"/api/v1/workout-exercises/{workout_exercise.id}/sets",
        {
            "position": 1,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.django_db
def test_create_workout_set_returns_404_for_completed_workout():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    workout = Workout.objects.create(
        user=user,
        name="Тренировка",
        started_at=datetime(2026, 6, 18, 10, 0, tzinfo=timezone.utc),
        status=WorkoutStatus.COMPLETED,
    )
    chest = MuscleGroup.objects.create(code="chest", name="Грудь")
    exercise = Exercise.objects.create(
        name="Жим лёжа",
        primary_muscle_group=chest,
        is_system=True,
    )
    workout_exercise = WorkoutExercise.objects.create(
        workout=workout,
        exercise=exercise,
        position=1,
    )
    client = authenticate_client(user)

    response = client.post(
        f"/api/v1/workout-exercises/{workout_exercise.id}/sets",
        {
            "position": 1,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.django_db
def test_create_workout_set_rejects_duplicate_position():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    workout = Workout.objects.create(
        user=user,
        name="Тренировка",
        started_at=datetime(2026, 6, 18, 10, 0, tzinfo=timezone.utc),
    )
    chest = MuscleGroup.objects.create(code="chest", name="Грудь")
    exercise = Exercise.objects.create(
        name="Жим лёжа",
        primary_muscle_group=chest,
        is_system=True,
    )
    workout_exercise = WorkoutExercise.objects.create(
        workout=workout,
        exercise=exercise,
        position=1,
    )
    WorkoutSet.objects.create(
        workout_exercise=workout_exercise,
        position=1,
    )
    client = authenticate_client(user)

    response = client.post(
        f"/api/v1/workout-exercises/{workout_exercise.id}/sets",
        {
            "position": 1,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "position" in response.json()["error"]["fields"]


@pytest.mark.django_db
def test_create_workout_set_rejects_invalid_rpe():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    workout = Workout.objects.create(
        user=user,
        name="Тренировка",
        started_at=datetime(2026, 6, 18, 10, 0, tzinfo=timezone.utc),
    )
    chest = MuscleGroup.objects.create(code="chest", name="Грудь")
    exercise = Exercise.objects.create(
        name="Жим лёжа",
        primary_muscle_group=chest,
        is_system=True,
    )
    workout_exercise = WorkoutExercise.objects.create(
        workout=workout,
        exercise=exercise,
        position=1,
    )
    client = authenticate_client(user)

    response = client.post(
        f"/api/v1/workout-exercises/{workout_exercise.id}/sets",
        {
            "position": 1,
            "rpe": "11.00",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "rpe" in response.json()["error"]["fields"]


@pytest.mark.django_db
def test_patch_workout_set_updates_current_user_active_set():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    workout = Workout.objects.create(
        user=user,
        name="Тренировка",
        started_at=datetime(2026, 6, 18, 10, 0, tzinfo=timezone.utc),
    )
    chest = MuscleGroup.objects.create(code="chest", name="Грудь")
    exercise = Exercise.objects.create(
        name="Жим лёжа",
        primary_muscle_group=chest,
        is_system=True,
    )
    workout_exercise = WorkoutExercise.objects.create(
        workout=workout,
        exercise=exercise,
        position=1,
    )
    workout_set = WorkoutSet.objects.create(
        workout_exercise=workout_exercise,
        position=1,
    )
    client = authenticate_client(user)

    response = client.patch(
        f"/api/v1/workout-sets/{workout_set.id}",
        {
            "weight": "82.50",
            "repetitions": 7,
            "is_completed": True,
        },
        format="json",
    )

    body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert body["data"]["weight"] == "82.50"
    assert body["data"]["repetitions"] == 7
    assert body["data"]["is_completed"] is True
    assert body["data"]["completed_at"] is not None

    workout_set.refresh_from_db()
    workout.refresh_from_db()

    assert workout_set.completed_at is not None
    assert workout.server_version == 2


@pytest.mark.django_db
def test_patch_workout_set_can_uncomplete_set():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    workout = Workout.objects.create(
        user=user,
        name="Тренировка",
        started_at=datetime(2026, 6, 18, 10, 0, tzinfo=timezone.utc),
    )
    chest = MuscleGroup.objects.create(code="chest", name="Грудь")
    exercise = Exercise.objects.create(
        name="Жим лёжа",
        primary_muscle_group=chest,
        is_system=True,
    )
    workout_exercise = WorkoutExercise.objects.create(
        workout=workout,
        exercise=exercise,
        position=1,
    )
    workout_set = WorkoutSet.objects.create(
        workout_exercise=workout_exercise,
        position=1,
        is_completed=True,
        completed_at=datetime(2026, 6, 18, 10, 10, tzinfo=timezone.utc),
    )
    client = authenticate_client(user)

    response = client.patch(
        f"/api/v1/workout-sets/{workout_set.id}",
        {
            "is_completed": False,
        },
        format="json",
    )

    body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert body["data"]["is_completed"] is False
    assert body["data"]["completed_at"] is None

    workout_set.refresh_from_db()

    assert workout_set.completed_at is None


@pytest.mark.django_db
def test_patch_workout_set_returns_404_for_other_user_set():
    owner = User.objects.create_user(
        email="owner@example.com",
        password="strong-password-123",
    )
    viewer = User.objects.create_user(
        email="viewer@example.com",
        password="strong-password-123",
    )
    workout = Workout.objects.create(
        user=owner,
        name="Тренировка",
        started_at=datetime(2026, 6, 18, 10, 0, tzinfo=timezone.utc),
    )
    chest = MuscleGroup.objects.create(code="chest", name="Грудь")
    exercise = Exercise.objects.create(
        name="Жим лёжа",
        primary_muscle_group=chest,
        is_system=True,
    )
    workout_exercise = WorkoutExercise.objects.create(
        workout=workout,
        exercise=exercise,
        position=1,
    )
    workout_set = WorkoutSet.objects.create(
        workout_exercise=workout_exercise,
        position=1,
    )
    client = authenticate_client(viewer)

    response = client.patch(
        f"/api/v1/workout-sets/{workout_set.id}",
        {
            "repetitions": 10,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.django_db
def test_delete_workout_set_soft_deletes_current_user_set():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    workout = Workout.objects.create(
        user=user,
        name="Тренировка",
        started_at=datetime(2026, 6, 18, 10, 0, tzinfo=timezone.utc),
    )
    chest = MuscleGroup.objects.create(code="chest", name="Грудь")
    exercise = Exercise.objects.create(
        name="Жим лёжа",
        primary_muscle_group=chest,
        is_system=True,
    )
    workout_exercise = WorkoutExercise.objects.create(
        workout=workout,
        exercise=exercise,
        position=1,
    )
    workout_set = WorkoutSet.objects.create(
        workout_exercise=workout_exercise,
        position=1,
    )
    client = authenticate_client(user)

    response = client.delete(f"/api/v1/workout-sets/{workout_set.id}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["data"]["success"] is True

    workout_set.refresh_from_db()
    workout.refresh_from_db()

    assert workout_set.deleted_at is not None
    assert workout.server_version == 2

    active_response = client.get("/api/v1/workouts/active")

    assert active_response.json()["data"]["exercises"][0]["sets"] == []


@pytest.mark.django_db
def test_finish_workout_successfully():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    workout = Workout.objects.create(
        user=user,
        name="Тренировка",
        started_at=datetime(2026, 6, 18, 10, 0, tzinfo=timezone.utc),
    )
    client = authenticate_client(user)

    response = client.post(f"/api/v1/workouts/{workout.id}/finish")

    body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert body["data"]["status"] == WorkoutStatus.COMPLETED
    assert body["data"]["finished_at"] is not None
    assert body["data"]["duration_seconds"] >= 0
    assert body["data"]["server_version"] == 2

    workout.refresh_from_db()

    assert workout.status == WorkoutStatus.COMPLETED
    assert workout.finished_at is not None
    assert workout.duration_seconds >= 0
    assert workout.server_version == 2

    active_response = client.get("/api/v1/workouts/active")

    assert active_response.json()["data"] is None


@pytest.mark.django_db
def test_finish_workout_requires_authentication():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    workout = Workout.objects.create(
        user=user,
        name="Тренировка",
        started_at=datetime(2026, 6, 18, 10, 0, tzinfo=timezone.utc),
    )
    client = APIClient()

    response = client.post(f"/api/v1/workouts/{workout.id}/finish")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["error"]["code"] == "NOT_AUTHENTICATED"


@pytest.mark.django_db
def test_finish_workout_returns_404_for_other_user_workout():
    owner = User.objects.create_user(
        email="owner@example.com",
        password="strong-password-123",
    )
    viewer = User.objects.create_user(
        email="viewer@example.com",
        password="strong-password-123",
    )
    workout = Workout.objects.create(
        user=owner,
        name="Тренировка",
        started_at=datetime(2026, 6, 18, 10, 0, tzinfo=timezone.utc),
    )
    client = authenticate_client(viewer)

    response = client.post(f"/api/v1/workouts/{workout.id}/finish")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["error"]["code"] == "NOT_FOUND"

    workout.refresh_from_db()

    assert workout.status == WorkoutStatus.ACTIVE


@pytest.mark.django_db
def test_finish_workout_returns_404_when_already_finished():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    workout = Workout.objects.create(
        user=user,
        name="Тренировка",
        started_at=datetime(2026, 6, 18, 10, 0, tzinfo=timezone.utc),
        status=WorkoutStatus.COMPLETED,
        finished_at=datetime(2026, 6, 18, 11, 0, tzinfo=timezone.utc),
        duration_seconds=3600,
    )
    client = authenticate_client(user)

    response = client.post(f"/api/v1/workouts/{workout.id}/finish")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.django_db
def test_cancel_workout_successfully():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    workout = Workout.objects.create(
        user=user,
        name="Тренировка",
        started_at=datetime(2026, 6, 18, 10, 0, tzinfo=timezone.utc),
    )
    client = authenticate_client(user)

    response = client.post(f"/api/v1/workouts/{workout.id}/cancel")

    body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert body["data"]["status"] == WorkoutStatus.CANCELLED
    assert body["data"]["finished_at"] is not None
    assert body["data"]["duration_seconds"] >= 0
    assert body["data"]["server_version"] == 2

    workout.refresh_from_db()

    assert workout.status == WorkoutStatus.CANCELLED
    assert workout.finished_at is not None
    assert workout.duration_seconds >= 0
    assert workout.server_version == 2

    active_response = client.get("/api/v1/workouts/active")

    assert active_response.json()["data"] is None


@pytest.mark.django_db
def test_cancel_workout_returns_404_for_other_user_workout():
    owner = User.objects.create_user(
        email="owner@example.com",
        password="strong-password-123",
    )
    viewer = User.objects.create_user(
        email="viewer@example.com",
        password="strong-password-123",
    )
    workout = Workout.objects.create(
        user=owner,
        name="Тренировка",
        started_at=datetime(2026, 6, 18, 10, 0, tzinfo=timezone.utc),
    )
    client = authenticate_client(viewer)

    response = client.post(f"/api/v1/workouts/{workout.id}/cancel")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["error"]["code"] == "NOT_FOUND"

    workout.refresh_from_db()

    assert workout.status == WorkoutStatus.ACTIVE


@pytest.mark.django_db
def test_get_workouts_requires_authentication():
    client = APIClient()

    response = client.get("/api/v1/workouts")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["error"]["code"] == "NOT_AUTHENTICATED"


@pytest.mark.django_db
def test_get_workouts_returns_only_current_user_non_deleted_workouts_ordered():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    other_user = User.objects.create_user(
        email="other@example.com",
        password="strong-password-123",
    )
    older = Workout.objects.create(
        user=user,
        name="Старая",
        started_at=datetime(2026, 6, 17, 10, 0, tzinfo=timezone.utc),
        status=WorkoutStatus.COMPLETED,
    )
    latest = Workout.objects.create(
        user=user,
        name="Новая",
        started_at=datetime(2026, 6, 18, 10, 0, tzinfo=timezone.utc),
        status=WorkoutStatus.ACTIVE,
    )
    Workout.objects.create(
        user=user,
        name="Удалённая",
        started_at=datetime(2026, 6, 19, 10, 0, tzinfo=timezone.utc),
        deleted_at=datetime(2026, 6, 19, 11, 0, tzinfo=timezone.utc),
    )
    Workout.objects.create(
        user=other_user,
        name="Чужая",
        started_at=datetime(2026, 6, 20, 10, 0, tzinfo=timezone.utc),
    )
    client = authenticate_client(user)

    response = client.get("/api/v1/workouts")

    body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert body["meta"]["count"] == 2
    assert [item["id"] for item in body["data"]] == [str(latest.id), str(older.id)]
    assert [item["name"] for item in body["data"]] == ["Новая", "Старая"]


@pytest.mark.django_db
def test_get_workouts_filters_by_status_and_date_range():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    Workout.objects.create(
        user=user,
        name="Before",
        started_at=datetime(2026, 6, 16, 10, 0, tzinfo=timezone.utc),
        status=WorkoutStatus.COMPLETED,
    )
    matching = Workout.objects.create(
        user=user,
        name="Matching",
        started_at=datetime(2026, 6, 18, 10, 0, tzinfo=timezone.utc),
        status=WorkoutStatus.COMPLETED,
    )
    Workout.objects.create(
        user=user,
        name="Active",
        started_at=datetime(2026, 6, 18, 12, 0, tzinfo=timezone.utc),
        status=WorkoutStatus.ACTIVE,
    )
    Workout.objects.create(
        user=user,
        name="After",
        started_at=datetime(2026, 6, 20, 10, 0, tzinfo=timezone.utc),
        status=WorkoutStatus.COMPLETED,
    )
    client = authenticate_client(user)

    response = client.get(
        "/api/v1/workouts",
        {
            "status": WorkoutStatus.COMPLETED,
            "date_from": "2026-06-17",
            "date_to": "2026-06-19",
        },
    )

    body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert body["meta"]["count"] == 1
    assert body["data"][0]["id"] == str(matching.id)
    assert body["data"][0]["name"] == "Matching"


@pytest.mark.django_db
def test_get_workouts_supports_limit_offset_pagination():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    latest = Workout.objects.create(
        user=user,
        name="Latest",
        started_at=datetime(2026, 6, 20, 10, 0, tzinfo=timezone.utc),
    )
    middle = Workout.objects.create(
        user=user,
        name="Middle",
        started_at=datetime(2026, 6, 19, 10, 0, tzinfo=timezone.utc),
    )
    Workout.objects.create(
        user=user,
        name="Oldest",
        started_at=datetime(2026, 6, 18, 10, 0, tzinfo=timezone.utc),
    )
    client = authenticate_client(user)

    response = client.get("/api/v1/workouts?limit=1&offset=1")

    body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert body["meta"] == {
        "count": 1,
        "total_count": 3,
        "limit": 1,
        "offset": 1,
    }
    assert [item["id"] for item in body["data"]] == [str(middle.id)]
    assert body["data"][0]["id"] != str(latest.id)


@pytest.mark.django_db
def test_get_workout_detail_returns_current_user_workout_with_nested_data():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    workout = Workout.objects.create(
        user=user,
        name="Тренировка",
        started_at=datetime(2026, 6, 18, 10, 0, tzinfo=timezone.utc),
    )
    chest = MuscleGroup.objects.create(code="chest", name="Грудь")
    exercise = Exercise.objects.create(
        name="Жим лёжа",
        primary_muscle_group=chest,
        is_system=True,
    )
    workout_exercise = WorkoutExercise.objects.create(
        workout=workout,
        exercise=exercise,
        position=1,
    )
    visible_set = WorkoutSet.objects.create(
        workout_exercise=workout_exercise,
        position=1,
        repetitions=8,
    )
    WorkoutSet.objects.create(
        workout_exercise=workout_exercise,
        position=2,
        repetitions=6,
        deleted_at=datetime(2026, 6, 18, 11, 0, tzinfo=timezone.utc),
    )
    client = authenticate_client(user)

    response = client.get(f"/api/v1/workouts/{workout.id}")

    body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert body["data"]["id"] == str(workout.id)
    assert body["data"]["name"] == "Тренировка"
    assert len(body["data"]["exercises"]) == 1
    assert body["data"]["exercises"][0]["exercise_id"] == str(exercise.id)
    assert len(body["data"]["exercises"][0]["sets"]) == 1
    assert body["data"]["exercises"][0]["sets"][0]["id"] == str(visible_set.id)


@pytest.mark.django_db
def test_get_workout_detail_returns_calculated_metrics():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    workout = Workout.objects.create(
        user=user,
        name="Тренировка",
        started_at=datetime(2026, 6, 18, 10, 0, tzinfo=timezone.utc),
    )
    chest = MuscleGroup.objects.create(code="chest", name="Грудь")
    exercise = Exercise.objects.create(
        name="Жим лёжа",
        primary_muscle_group=chest,
        is_system=True,
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
        repetitions=6,
        is_completed=True,
    )
    WorkoutSet.objects.create(
        workout_exercise=workout_exercise,
        position=2,
        set_type=WorkoutSetType.WORKING,
        weight="80.00",
        repetitions=10,
        is_completed=True,
    )
    WorkoutSet.objects.create(
        workout_exercise=workout_exercise,
        position=3,
        set_type=WorkoutSetType.WARMUP,
        weight="60.00",
        repetitions=10,
        is_completed=True,
    )
    WorkoutSet.objects.create(
        workout_exercise=workout_exercise,
        position=4,
        set_type=WorkoutSetType.WORKING,
        weight="120.00",
        repetitions=1,
        is_completed=False,
    )
    client = authenticate_client(user)

    response = client.get(f"/api/v1/workouts/{workout.id}")

    metrics = response.json()["data"]["metrics"]

    assert response.status_code == status.HTTP_200_OK
    assert metrics == {
        "total_volume": "1400.00",
        "completed_working_sets": 2,
        "best_estimated_one_rep_max": "120.00",
    }


@pytest.mark.django_db
def test_get_workout_detail_returns_404_for_other_user_workout():
    owner = User.objects.create_user(
        email="owner@example.com",
        password="strong-password-123",
    )
    viewer = User.objects.create_user(
        email="viewer@example.com",
        password="strong-password-123",
    )
    workout = Workout.objects.create(
        user=owner,
        name="Чужая",
        started_at=datetime(2026, 6, 18, 10, 0, tzinfo=timezone.utc),
    )
    client = authenticate_client(viewer)

    response = client.get(f"/api/v1/workouts/{workout.id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.django_db
def test_get_workout_detail_returns_404_for_deleted_workout():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    workout = Workout.objects.create(
        user=user,
        name="Удалённая",
        started_at=datetime(2026, 6, 18, 10, 0, tzinfo=timezone.utc),
        deleted_at=datetime(2026, 6, 18, 11, 0, tzinfo=timezone.utc),
    )
    client = authenticate_client(user)

    response = client.get(f"/api/v1/workouts/{workout.id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.django_db
def test_finish_workout_creates_personal_records():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    workout = Workout.objects.create(
        user=user,
        name="Тренировка",
        started_at=datetime(2026, 6, 18, 10, 0, tzinfo=timezone.utc),
    )
    chest = MuscleGroup.objects.create(code="chest", name="Грудь")
    exercise = Exercise.objects.create(
        name="Жим лёжа",
        primary_muscle_group=chest,
        is_system=True,
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
        repetitions=6,
        is_completed=True,
        completed_at=datetime(2026, 6, 18, 10, 30, tzinfo=timezone.utc),
    )
    client = authenticate_client(user)

    response = client.post(f"/api/v1/workouts/{workout.id}/finish")

    assert response.status_code == status.HTTP_200_OK

    records = PersonalRecord.objects.filter(user=user, exercise=exercise, is_current=True)

    assert records.count() == 4
    assert records.get(record_type=PersonalRecordType.MAX_WEIGHT).value == 100
    assert records.get(record_type=PersonalRecordType.MAX_REPS_WITH_WEIGHT).value == 6
    assert records.get(record_type=PersonalRecordType.BEST_SET_VOLUME).value == 600
    assert records.get(record_type=PersonalRecordType.ESTIMATED_ONE_REP_MAX).value == 120


@pytest.mark.django_db
def test_finish_later_workout_recalculates_current_personal_records():
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
    first_workout = Workout.objects.create(
        user=user,
        name="Первая",
        started_at=datetime(2026, 6, 17, 10, 0, tzinfo=timezone.utc),
    )
    first_workout_exercise = WorkoutExercise.objects.create(
        workout=first_workout,
        exercise=exercise,
        position=1,
    )
    WorkoutSet.objects.create(
        workout_exercise=first_workout_exercise,
        position=1,
        set_type=WorkoutSetType.WORKING,
        weight="100.00",
        repetitions=5,
        is_completed=True,
        completed_at=datetime(2026, 6, 17, 10, 30, tzinfo=timezone.utc),
    )
    second_workout = Workout.objects.create(
        user=user,
        name="Вторая",
        started_at=datetime(2026, 6, 18, 10, 0, tzinfo=timezone.utc),
    )
    second_workout_exercise = WorkoutExercise.objects.create(
        workout=second_workout,
        exercise=exercise,
        position=1,
    )
    WorkoutSet.objects.create(
        workout_exercise=second_workout_exercise,
        position=1,
        set_type=WorkoutSetType.WORKING,
        weight="110.00",
        repetitions=4,
        is_completed=True,
        completed_at=datetime(2026, 6, 18, 10, 30, tzinfo=timezone.utc),
    )
    client = authenticate_client(user)

    first_response = client.post(f"/api/v1/workouts/{first_workout.id}/finish")
    second_response = client.post(f"/api/v1/workouts/{second_workout.id}/finish")

    assert first_response.status_code == status.HTTP_200_OK
    assert second_response.status_code == status.HTTP_200_OK

    current_max_weight = PersonalRecord.objects.get(
        user=user,
        exercise=exercise,
        record_type=PersonalRecordType.MAX_WEIGHT,
        is_current=True,
    )

    assert current_max_weight.value == 110
    assert PersonalRecord.objects.filter(
        user=user,
        exercise=exercise,
        record_type=PersonalRecordType.MAX_WEIGHT,
        is_current=False,
    ).exists()


@pytest.mark.django_db
def test_get_personal_records_requires_authentication():
    client = APIClient()

    response = client.get("/api/v1/personal-records")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["error"]["code"] == "NOT_AUTHENTICATED"


@pytest.mark.django_db
def test_get_personal_records_returns_current_user_records_only():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
    )
    other_user = User.objects.create_user(
        email="other@example.com",
        password="strong-password-123",
    )
    chest = MuscleGroup.objects.create(code="chest", name="Грудь")
    exercise = Exercise.objects.create(
        name="Жим лёжа",
        primary_muscle_group=chest,
        is_system=True,
    )
    workout = Workout.objects.create(
        user=user,
        name="Тренировка",
        started_at=datetime(2026, 6, 18, 10, 0, tzinfo=timezone.utc),
        status=WorkoutStatus.COMPLETED,
    )
    workout_exercise = WorkoutExercise.objects.create(
        workout=workout,
        exercise=exercise,
        position=1,
    )
    workout_set = WorkoutSet.objects.create(
        workout_exercise=workout_exercise,
        position=1,
        set_type=WorkoutSetType.WORKING,
        weight="100.00",
        repetitions=6,
        is_completed=True,
        completed_at=datetime(2026, 6, 18, 10, 30, tzinfo=timezone.utc),
    )
    record = PersonalRecord.objects.create(
        user=user,
        exercise=exercise,
        workout_set=workout_set,
        record_type=PersonalRecordType.MAX_WEIGHT,
        value="100.00",
        unit="kg",
        achieved_at=workout_set.completed_at,
    )
    PersonalRecord.objects.create(
        user=other_user,
        exercise=exercise,
        workout_set=workout_set,
        record_type=PersonalRecordType.BEST_SET_VOLUME,
        value="600.00",
        unit="kg",
        achieved_at=workout_set.completed_at,
    )
    client = authenticate_client(user)

    response = client.get("/api/v1/personal-records")

    body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert body["meta"]["count"] == 1
    assert body["data"][0]["id"] == str(record.id)
    assert body["data"][0]["exercise_id"] == str(exercise.id)
    assert body["data"][0]["workout_set_id"] == str(workout_set.id)
    assert body["data"][0]["record_type"] == PersonalRecordType.MAX_WEIGHT
    assert body["data"][0]["value"] == "100.00"


@pytest.mark.django_db
def test_get_personal_records_filters_by_exercise_and_type():
    user = User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
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
    workout = Workout.objects.create(
        user=user,
        name="Тренировка",
        started_at=datetime(2026, 6, 18, 10, 0, tzinfo=timezone.utc),
        status=WorkoutStatus.COMPLETED,
    )
    first_workout_exercise = WorkoutExercise.objects.create(
        workout=workout,
        exercise=first_exercise,
        position=1,
    )
    second_workout_exercise = WorkoutExercise.objects.create(
        workout=workout,
        exercise=second_exercise,
        position=2,
    )
    first_set = WorkoutSet.objects.create(
        workout_exercise=first_workout_exercise,
        position=1,
        set_type=WorkoutSetType.WORKING,
        weight="100.00",
        repetitions=6,
        is_completed=True,
        completed_at=datetime(2026, 6, 18, 10, 30, tzinfo=timezone.utc),
    )
    second_set = WorkoutSet.objects.create(
        workout_exercise=second_workout_exercise,
        position=1,
        set_type=WorkoutSetType.WORKING,
        weight="120.00",
        repetitions=5,
        is_completed=True,
        completed_at=datetime(2026, 6, 18, 10, 40, tzinfo=timezone.utc),
    )
    matching = PersonalRecord.objects.create(
        user=user,
        exercise=first_exercise,
        workout_set=first_set,
        record_type=PersonalRecordType.MAX_WEIGHT,
        value="100.00",
        unit="kg",
        achieved_at=first_set.completed_at,
    )
    PersonalRecord.objects.create(
        user=user,
        exercise=second_exercise,
        workout_set=second_set,
        record_type=PersonalRecordType.MAX_WEIGHT,
        value="120.00",
        unit="kg",
        achieved_at=second_set.completed_at,
    )
    client = authenticate_client(user)

    response = client.get(
        "/api/v1/personal-records",
        {
            "exercise_id": str(first_exercise.id),
            "record_type": PersonalRecordType.MAX_WEIGHT,
        },
    )

    body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert body["meta"]["count"] == 1
    assert body["data"][0]["id"] == str(matching.id)
