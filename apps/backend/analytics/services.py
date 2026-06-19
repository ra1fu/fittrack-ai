from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Prefetch

from nutrition.views import _build_day_target_summary, _calculate_day_totals
from workouts.calculations import calculate_workout_metrics
from workouts.models import WorkoutSet, WorkoutStatus


def build_dashboard_summary(*, user, summary_date: date) -> dict:
    week_start = summary_date - timedelta(days=summary_date.weekday())
    week_end = week_start + timedelta(days=6)

    return {
        "date": summary_date.isoformat(),
        "nutrition": _build_nutrition_summary(user=user, summary_date=summary_date),
        "workouts": _build_workout_summary(
            user=user,
            week_start=week_start,
            week_end=week_end,
        ),
    }


def build_dashboard_trends(*, user, date_from: date, date_to: date) -> dict:
    points = []
    current_date = date_from

    nutrition_by_date = _build_nutrition_totals_by_date(
        user=user,
        date_from=date_from,
        date_to=date_to,
    )
    workout_by_date = _build_workout_totals_by_date(
        user=user,
        date_from=date_from,
        date_to=date_to,
    )

    while current_date <= date_to:
        date_key = current_date.isoformat()
        points.append(
            {
                "date": date_key,
                "nutrition": nutrition_by_date.get(
                    date_key,
                    _empty_nutrition_totals(),
                ),
                "workouts": workout_by_date.get(
                    date_key,
                    _empty_workout_totals(),
                ),
            }
        )
        current_date += timedelta(days=1)

    return {
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "points": points,
    }


def _build_nutrition_summary(*, user, summary_date: date) -> dict:
    meals = (
        user.meals.filter(meal_date=summary_date)
        .prefetch_related("items")
        .order_by("eaten_at", "created_at")
    )
    totals = _calculate_day_totals(meals)
    target_summary = _build_day_target_summary(user, summary_date, totals)

    return {
        "totals": totals,
        "targets": target_summary["targets"],
        "progress": target_summary["progress"],
        "meal_count": meals.count(),
    }


def _build_nutrition_totals_by_date(*, user, date_from: date, date_to: date) -> dict:
    meals = (
        user.meals.filter(
            meal_date__gte=date_from,
            meal_date__lte=date_to,
        )
        .prefetch_related("items")
        .order_by("meal_date", "created_at")
    )
    totals_by_date = {}

    for meal in meals:
        date_key = meal.meal_date.isoformat()
        if date_key not in totals_by_date:
            totals_by_date[date_key] = _empty_nutrition_totals()

        meal_totals = _calculate_day_totals([meal])
        totals_by_date[date_key]["calories"] = _add_decimal_strings(
            totals_by_date[date_key]["calories"],
            meal_totals["calories"],
        )
        totals_by_date[date_key]["protein"] = _add_decimal_strings(
            totals_by_date[date_key]["protein"],
            meal_totals["protein"],
        )
        totals_by_date[date_key]["fat"] = _add_decimal_strings(
            totals_by_date[date_key]["fat"],
            meal_totals["fat"],
        )
        totals_by_date[date_key]["carbs"] = _add_decimal_strings(
            totals_by_date[date_key]["carbs"],
            meal_totals["carbs"],
        )
        totals_by_date[date_key]["meal_count"] += 1

    return totals_by_date


def _build_workout_summary(*, user, week_start: date, week_end: date) -> dict:
    workouts = (
        user.workouts.filter(
            started_at__date__gte=week_start,
            started_at__date__lte=week_end,
            deleted_at__isnull=True,
        )
        .prefetch_related(
            Prefetch(
                "exercises__sets",
                queryset=WorkoutSet.objects.filter(deleted_at__isnull=True),
            )
        )
        .order_by("started_at", "created_at")
    )
    completed_workouts = [
        workout
        for workout in workouts
        if workout.status == WorkoutStatus.COMPLETED
    ]

    total_volume = Decimal("0.00")
    completed_sets = 0
    duration_seconds = 0

    for workout in completed_workouts:
        metrics = calculate_workout_metrics(workout)
        total_volume += Decimal(metrics["total_volume"])
        completed_sets += metrics["completed_working_sets"]
        duration_seconds += workout.duration_seconds or 0

    return {
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "completed_workouts": len(completed_workouts),
        "total_volume": f"{total_volume:.2f}",
        "completed_working_sets": completed_sets,
        "duration_seconds": duration_seconds,
    }


def _build_workout_totals_by_date(*, user, date_from: date, date_to: date) -> dict:
    workouts = (
        user.workouts.filter(
            started_at__date__gte=date_from,
            started_at__date__lte=date_to,
            status=WorkoutStatus.COMPLETED,
            deleted_at__isnull=True,
        )
        .prefetch_related(
            Prefetch(
                "exercises__sets",
                queryset=WorkoutSet.objects.filter(deleted_at__isnull=True),
            )
        )
        .order_by("started_at", "created_at")
    )
    totals_by_date = {}

    for workout in workouts:
        date_key = workout.started_at.date().isoformat()
        if date_key not in totals_by_date:
            totals_by_date[date_key] = _empty_workout_totals()

        metrics = calculate_workout_metrics(workout)
        totals_by_date[date_key]["completed_workouts"] += 1
        totals_by_date[date_key]["total_volume"] = _add_decimal_strings(
            totals_by_date[date_key]["total_volume"],
            metrics["total_volume"],
        )
        totals_by_date[date_key]["completed_working_sets"] += metrics[
            "completed_working_sets"
        ]
        totals_by_date[date_key]["duration_seconds"] += workout.duration_seconds or 0

    return totals_by_date


def _empty_nutrition_totals() -> dict:
    return {
        "calories": "0.00",
        "protein": "0.00",
        "fat": "0.00",
        "carbs": "0.00",
        "meal_count": 0,
    }


def _empty_workout_totals() -> dict:
    return {
        "completed_workouts": 0,
        "total_volume": "0.00",
        "completed_working_sets": 0,
        "duration_seconds": 0,
    }


def _add_decimal_strings(left: str, right: str) -> str:
    return f"{Decimal(left) + Decimal(right):.2f}"
