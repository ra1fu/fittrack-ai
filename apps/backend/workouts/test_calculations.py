from decimal import Decimal

from workouts.calculations import (
    calculate_estimated_one_rep_max,
    calculate_set_volume,
    is_estimated_one_rep_max_low_confidence,
)
from workouts.models import WorkoutSet, WorkoutSetType


def make_workout_set(
    *,
    weight=None,
    repetitions=None,
    set_type=WorkoutSetType.WORKING,
    is_completed=True,
    deleted_at=None,
):
    return WorkoutSet(
        weight=weight,
        repetitions=repetitions,
        set_type=set_type,
        is_completed=is_completed,
        deleted_at=deleted_at,
    )


def test_calculate_set_volume_for_completed_working_set():
    workout_set = make_workout_set(
        weight=Decimal("80.00"),
        repetitions=8,
    )

    assert calculate_set_volume(workout_set) == Decimal("640.00")


def test_calculate_set_volume_ignores_incomplete_warmup_and_missing_values():
    assert calculate_set_volume(
        make_workout_set(weight=Decimal("80.00"), repetitions=8, is_completed=False)
    ) == Decimal("0.00")
    assert calculate_set_volume(
        make_workout_set(
            weight=Decimal("80.00"),
            repetitions=8,
            set_type=WorkoutSetType.WARMUP,
        )
    ) == Decimal("0.00")
    assert calculate_set_volume(
        make_workout_set(weight=None, repetitions=8)
    ) == Decimal("0.00")
    assert calculate_set_volume(
        make_workout_set(weight=Decimal("80.00"), repetitions=None)
    ) == Decimal("0.00")


def test_calculate_estimated_one_rep_max_uses_epley_formula():
    workout_set = make_workout_set(
        weight=Decimal("100.00"),
        repetitions=6,
    )

    assert calculate_estimated_one_rep_max(workout_set) == Decimal("120.00")


def test_calculate_estimated_one_rep_max_returns_none_for_ineligible_set():
    workout_set = make_workout_set(
        weight=Decimal("100.00"),
        repetitions=6,
        is_completed=False,
    )

    assert calculate_estimated_one_rep_max(workout_set) is None


def test_estimated_one_rep_max_low_confidence_threshold():
    assert is_estimated_one_rep_max_low_confidence(12) is False
    assert is_estimated_one_rep_max_low_confidence(13) is True
    assert is_estimated_one_rep_max_low_confidence(None) is False
