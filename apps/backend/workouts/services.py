from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from routines.models import RoutineDay
from workouts.models import (
    Workout,
    WorkoutExercise,
    WorkoutSet,
    WorkoutSetType,
)


@dataclass(frozen=True)
class StartWorkoutCommand:
    user_id: UUID
    name: str | None = None
    source_routine_day_id: UUID | None = None
    started_at: datetime | None = None
    notes: str = ""
    local_device_id: UUID | None = None
    client_updated_at: datetime | None = None


def get_user_routine_day_or_none(user, routine_day_id):
    if routine_day_id is None:
        return None

    try:
        return (
            RoutineDay.objects.select_related("routine")
            .prefetch_related("exercises__exercise")
            .get(
                id=routine_day_id,
                routine__user=user,
                routine__deleted_at__isnull=True,
            )
        )
    except RoutineDay.DoesNotExist:
        return None


@transaction.atomic
def start_workout(user, command: StartWorkoutCommand) -> Workout:
    if command.local_device_id is not None:
        existing_workout = Workout.objects.filter(
            user=user,
            local_device_id=command.local_device_id,
            deleted_at__isnull=True,
        ).first()

        if existing_workout is not None:
            return existing_workout

    routine_day = get_user_routine_day_or_none(user, command.source_routine_day_id)

    if command.source_routine_day_id is not None and routine_day is None:
        raise RoutineDay.DoesNotExist

    started_at = command.started_at or timezone.now()
    name = command.name or (routine_day.name if routine_day is not None else "Тренировка")

    workout = Workout.objects.create(
        user=user,
        source_routine=routine_day.routine if routine_day is not None else None,
        source_routine_day=routine_day,
        name=name,
        started_at=started_at,
        notes=command.notes,
        local_device_id=command.local_device_id,
        client_updated_at=command.client_updated_at,
    )

    if routine_day is None:
        return workout

    routine_exercises = routine_day.exercises.select_related("exercise").order_by(
        "position",
        "created_at",
    )

    for routine_exercise in routine_exercises:
        workout_exercise = WorkoutExercise.objects.create(
            workout=workout,
            exercise=routine_exercise.exercise,
            source_routine_exercise=routine_exercise,
            position=routine_exercise.position,
            notes=routine_exercise.notes,
            superset_group=routine_exercise.superset_group,
        )

        for set_position in range(1, routine_exercise.planned_sets + 1):
            WorkoutSet.objects.create(
                workout_exercise=workout_exercise,
                position=set_position,
                set_type=WorkoutSetType.WORKING,
                weight=routine_exercise.target_weight,
                repetitions=routine_exercise.rep_min,
                rpe=routine_exercise.target_rpe,
                rir=routine_exercise.target_rir,
            )

    return workout
