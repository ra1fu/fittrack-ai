from decimal import Decimal

from django.db import transaction

from workouts.calculations import (
    calculate_estimated_one_rep_max,
    calculate_set_volume,
)
from workouts.models import (
    PersonalRecord,
    PersonalRecordType,
    WorkoutSet,
    WorkoutSetType,
    WorkoutStatus,
)


RECORD_UNITS = {
    PersonalRecordType.MAX_WEIGHT: "kg",
    PersonalRecordType.MAX_REPS_WITH_WEIGHT: "reps",
    PersonalRecordType.BEST_SET_VOLUME: "kg",
    PersonalRecordType.ESTIMATED_ONE_REP_MAX: "kg",
}


@transaction.atomic
def recalculate_personal_records_for_workout(workout):
    exercise_ids = list(
        workout.exercises.values_list("exercise_id", flat=True).distinct()
    )

    if not exercise_ids:
        return

    record_types = [record_type for record_type, _ in PersonalRecordType.choices]

    PersonalRecord.objects.filter(
        user=workout.user,
        exercise_id__in=exercise_ids,
        record_type__in=record_types,
        is_current=True,
    ).update(is_current=False)

    for exercise_id in exercise_ids:
        eligible_sets = _get_eligible_sets(workout.user, exercise_id)

        _create_current_record(
            user=workout.user,
            exercise_id=exercise_id,
            record_type=PersonalRecordType.MAX_WEIGHT,
            candidate=_get_max_weight_candidate(eligible_sets),
        )
        _create_current_record(
            user=workout.user,
            exercise_id=exercise_id,
            record_type=PersonalRecordType.MAX_REPS_WITH_WEIGHT,
            candidate=_get_max_reps_with_weight_candidate(eligible_sets),
        )
        _create_current_record(
            user=workout.user,
            exercise_id=exercise_id,
            record_type=PersonalRecordType.BEST_SET_VOLUME,
            candidate=_get_best_set_volume_candidate(eligible_sets),
        )
        _create_current_record(
            user=workout.user,
            exercise_id=exercise_id,
            record_type=PersonalRecordType.ESTIMATED_ONE_REP_MAX,
            candidate=_get_best_estimated_one_rep_max_candidate(eligible_sets),
        )


def _get_eligible_sets(user, exercise_id):
    return list(
        WorkoutSet.objects.select_related(
            "workout_exercise",
            "workout_exercise__workout",
        ).filter(
            workout_exercise__workout__user=user,
            workout_exercise__workout__status=WorkoutStatus.COMPLETED,
            workout_exercise__workout__deleted_at__isnull=True,
            workout_exercise__exercise_id=exercise_id,
            deleted_at__isnull=True,
            is_completed=True,
            set_type=WorkoutSetType.WORKING,
            weight__isnull=False,
            weight__gt=0,
            repetitions__isnull=False,
            repetitions__gt=0,
        )
    )


def _get_max_weight_candidate(workout_sets):
    return _max_candidate(
        workout_sets,
        value_getter=lambda workout_set: workout_set.weight,
        tie_breaker=lambda workout_set: workout_set.repetitions or 0,
    )


def _get_max_reps_with_weight_candidate(workout_sets):
    return _max_candidate(
        workout_sets,
        value_getter=lambda workout_set: Decimal(workout_set.repetitions),
        tie_breaker=lambda workout_set: workout_set.weight or Decimal("0.00"),
    )


def _get_best_set_volume_candidate(workout_sets):
    return _max_candidate(
        workout_sets,
        value_getter=calculate_set_volume,
        tie_breaker=lambda workout_set: workout_set.weight or Decimal("0.00"),
    )


def _get_best_estimated_one_rep_max_candidate(workout_sets):
    candidates = []

    for workout_set in workout_sets:
        value = calculate_estimated_one_rep_max(workout_set)
        if value is None:
            continue

        candidates.append((workout_set, value))

    if not candidates:
        return None

    return max(
        candidates,
        key=lambda item: (
            item[1],
            item[0].weight or Decimal("0.00"),
            item[0].repetitions or 0,
        ),
    )


def _max_candidate(workout_sets, value_getter, tie_breaker):
    candidates = []

    for workout_set in workout_sets:
        value = value_getter(workout_set)
        if value is None:
            continue

        candidates.append((workout_set, value))

    if not candidates:
        return None

    return max(candidates, key=lambda item: (item[1], tie_breaker(item[0])))


def _create_current_record(user, exercise_id, record_type, candidate):
    if candidate is None:
        return

    workout_set, value = candidate

    PersonalRecord.objects.create(
        user=user,
        exercise_id=exercise_id,
        workout_set=workout_set,
        record_type=record_type,
        value=value,
        unit=RECORD_UNITS[record_type],
        achieved_at=workout_set.completed_at or workout_set.created_at,
        is_current=True,
    )
