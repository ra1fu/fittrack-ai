import uuid

from django.conf import settings
from django.db import models

from exercises.models import Exercise


class Routine(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="routines",
    )

    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=32, blank=True)

    is_active = models.BooleanField(default=True)
    version = models.PositiveIntegerField(default=1)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "routines_routine"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["user", "deleted_at"]),
        ]

    def __str__(self) -> str:
        return self.name


class RoutineDay(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    routine = models.ForeignKey(
        Routine,
        on_delete=models.CASCADE,
        related_name="days",
    )

    name = models.CharField(max_length=160)
    position = models.PositiveIntegerField()
    planned_weekday = models.PositiveSmallIntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "routines_routine_day"
        ordering = ["position", "created_at"]
        indexes = [
            models.Index(fields=["routine", "position"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["routine", "position"],
                name="routine_day_position_unique_per_routine",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(planned_weekday__isnull=True)
                    | (
                        models.Q(planned_weekday__gte=1)
                        & models.Q(planned_weekday__lte=7)
                    )
                ),
                name="routine_day_planned_weekday_between_1_and_7_or_null",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class RoutineExercise(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    routine_day = models.ForeignKey(
        RoutineDay,
        on_delete=models.CASCADE,
        related_name="exercises",
    )
    exercise = models.ForeignKey(
        Exercise,
        on_delete=models.PROTECT,
        related_name="routine_exercises",
    )

    position = models.PositiveIntegerField()
    planned_sets = models.PositiveSmallIntegerField(default=3)
    rep_min = models.PositiveSmallIntegerField(null=True, blank=True)
    rep_max = models.PositiveSmallIntegerField(null=True, blank=True)
    target_weight = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
    )
    target_rpe = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
    )
    target_rir = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
    )
    rest_seconds = models.PositiveIntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)
    superset_group = models.CharField(max_length=32, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "routines_routine_exercise"
        ordering = ["position", "created_at"]
        indexes = [
            models.Index(fields=["routine_day", "position"]),
            models.Index(fields=["exercise"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["routine_day", "position"],
                name="routine_exercise_position_unique_per_day",
            ),
            models.CheckConstraint(
                condition=models.Q(planned_sets__gte=1),
                name="routine_exercise_planned_sets_positive",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(rep_min__isnull=True)
                    | models.Q(rep_max__isnull=True)
                    | models.Q(rep_min__lte=models.F("rep_max"))
                ),
                name="routine_exercise_rep_range_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(target_weight__isnull=True)
                | models.Q(target_weight__gte=0),
                name="routine_exercise_target_weight_non_negative_or_null",
            ),
            models.CheckConstraint(
                condition=models.Q(target_rpe__isnull=True)
                | (models.Q(target_rpe__gte=1) & models.Q(target_rpe__lte=10)),
                name="routine_exercise_target_rpe_between_1_and_10_or_null",
            ),
            models.CheckConstraint(
                condition=models.Q(target_rir__isnull=True)
                | (models.Q(target_rir__gte=0) & models.Q(target_rir__lte=10)),
                name="routine_exercise_target_rir_between_0_and_10_or_null",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.routine_day}: {self.exercise}"
