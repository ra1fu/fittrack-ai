from decimal import Decimal, ROUND_HALF_UP

from workouts.models import WorkoutSet, WorkoutSetType


ONE_REP_MAX_LOW_CONFIDENCE_REPS = 12


def calculate_set_volume(workout_set: WorkoutSet) -> Decimal:
    if not _is_volume_eligible_set(workout_set):
        return Decimal("0.00")

    return _quantize_decimal(workout_set.weight * workout_set.repetitions)


def calculate_estimated_one_rep_max(workout_set: WorkoutSet) -> Decimal | None:
    if not _is_volume_eligible_set(workout_set):
        return None

    value = workout_set.weight * (Decimal("1") + Decimal(workout_set.repetitions) / Decimal("30"))

    return _quantize_decimal(value)


def calculate_workout_metrics(workout) -> dict:
    total_volume = Decimal("0.00")
    completed_working_sets = 0
    best_estimated_one_rep_max = None

    for workout_exercise in workout.exercises.all():
        for workout_set in workout_exercise.sets.all():
            if workout_set.deleted_at is not None:
                continue

            set_volume = calculate_set_volume(workout_set)
            total_volume += set_volume

            if set_volume > 0:
                completed_working_sets += 1

            estimated_one_rep_max = calculate_estimated_one_rep_max(workout_set)
            if estimated_one_rep_max is None:
                continue

            if (
                best_estimated_one_rep_max is None
                or estimated_one_rep_max > best_estimated_one_rep_max
            ):
                best_estimated_one_rep_max = estimated_one_rep_max

    return {
        "total_volume": _format_decimal(total_volume),
        "completed_working_sets": completed_working_sets,
        "best_estimated_one_rep_max": _format_decimal(best_estimated_one_rep_max),
    }


def is_estimated_one_rep_max_low_confidence(repetitions: int | None) -> bool:
    if repetitions is None:
        return False

    return repetitions > ONE_REP_MAX_LOW_CONFIDENCE_REPS


def _is_volume_eligible_set(workout_set: WorkoutSet) -> bool:
    return (
        workout_set.deleted_at is None
        and workout_set.is_completed is True
        and workout_set.set_type == WorkoutSetType.WORKING
        and workout_set.weight is not None
        and workout_set.weight > 0
        and workout_set.repetitions is not None
        and workout_set.repetitions > 0
    )


def _quantize_decimal(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _format_decimal(value: Decimal | None) -> str | None:
    if value is None:
        return None

    return f"{_quantize_decimal(value):.2f}"
