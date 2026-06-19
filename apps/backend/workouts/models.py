import uuid

from django.conf import settings
from django.db import models

from exercises.models import Exercise
from routines.models import Routine, RoutineDay, RoutineExercise


class WorkoutStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"


class WorkoutSetType(models.TextChoices):
    WARMUP = "warmup", "Warmup"
    WORKING = "working", "Working"
    FAILURE = "failure", "Failure"
    DROP_SET = "drop_set", "Drop set"
    EXTRA = "extra", "Extra"
    SKIPPED = "skipped", "Skipped"


class Workout(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="workouts",
    )
    source_routine = models.ForeignKey(
        Routine,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="source_workouts",
    )
    source_routine_day = models.ForeignKey(
        RoutineDay,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="source_workouts",
    )

    name = models.CharField(max_length=160)
    status = models.CharField(
        max_length=32,
        choices=WorkoutStatus.choices,
        default=WorkoutStatus.ACTIVE,
    )
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)

    local_device_id = models.UUIDField(null=True, blank=True)
    client_updated_at = models.DateTimeField(null=True, blank=True)
    server_version = models.PositiveIntegerField(default=1)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "workouts_workout"
        ordering = ["-started_at", "-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["user", "started_at"]),
            models.Index(fields=["user", "deleted_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "local_device_id"],
                condition=models.Q(local_device_id__isnull=False),
                name="workout_local_device_id_unique_per_user",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class WorkoutExercise(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    workout = models.ForeignKey(
        Workout,
        on_delete=models.CASCADE,
        related_name="exercises",
    )
    exercise = models.ForeignKey(
        Exercise,
        on_delete=models.PROTECT,
        related_name="workout_exercises",
    )
    source_routine_exercise = models.ForeignKey(
        RoutineExercise,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="source_workout_exercises",
    )

    position = models.PositiveIntegerField()
    notes = models.TextField(blank=True)
    superset_group = models.CharField(max_length=32, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workouts_workout_exercise"
        ordering = ["position", "created_at"]
        indexes = [
            models.Index(fields=["workout", "position"]),
            models.Index(fields=["exercise"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["workout", "position"],
                name="workout_exercise_position_unique_per_workout",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.workout}: {self.exercise}"


class WorkoutSet(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    workout_exercise = models.ForeignKey(
        WorkoutExercise,
        on_delete=models.CASCADE,
        related_name="sets",
    )

    position = models.PositiveIntegerField()
    set_type = models.CharField(
        max_length=32,
        choices=WorkoutSetType.choices,
        default=WorkoutSetType.WORKING,
    )
    weight = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
    )
    repetitions = models.PositiveSmallIntegerField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    distance_meters = models.DecimalField(
        max_digits=9,
        decimal_places=2,
        null=True,
        blank=True,
    )
    rpe = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
    )
    rir = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
    )
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "workouts_workout_set"
        ordering = ["position", "created_at"]
        indexes = [
            models.Index(fields=["workout_exercise", "position"]),
            models.Index(fields=["is_completed"]),
            models.Index(fields=["deleted_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["workout_exercise", "position"],
                name="workout_set_position_unique_per_exercise",
            ),
            models.CheckConstraint(
                condition=models.Q(weight__isnull=True) | models.Q(weight__gte=0),
                name="workout_set_weight_non_negative_or_null",
            ),
            models.CheckConstraint(
                condition=models.Q(distance_meters__isnull=True)
                | models.Q(distance_meters__gte=0),
                name="workout_set_distance_non_negative_or_null",
            ),
            models.CheckConstraint(
                condition=models.Q(rpe__isnull=True)
                | (models.Q(rpe__gte=1) & models.Q(rpe__lte=10)),
                name="workout_set_rpe_between_1_and_10_or_null",
            ),
            models.CheckConstraint(
                condition=models.Q(rir__isnull=True)
                | (models.Q(rir__gte=0) & models.Q(rir__lte=10)),
                name="workout_set_rir_between_0_and_10_or_null",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.workout_exercise}: set {self.position}"


class PersonalRecordType(models.TextChoices):
    MAX_WEIGHT = "max_weight", "Max weight"
    MAX_REPS_WITH_WEIGHT = "max_reps_with_weight", "Max reps with weight"
    BEST_SET_VOLUME = "best_set_volume", "Best set volume"
    ESTIMATED_ONE_REP_MAX = "estimated_one_rep_max", "Estimated 1RM"


class PersonalRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="personal_records",
    )
    exercise = models.ForeignKey(
        Exercise,
        on_delete=models.CASCADE,
        related_name="personal_records",
    )
    workout_set = models.ForeignKey(
        WorkoutSet,
        on_delete=models.CASCADE,
        related_name="personal_records",
    )

    record_type = models.CharField(
        max_length=64,
        choices=PersonalRecordType.choices,
    )
    value = models.DecimalField(max_digits=12, decimal_places=2)
    unit = models.CharField(max_length=32)
    achieved_at = models.DateTimeField()
    is_current = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workouts_personal_record"
        ordering = ["exercise__name", "record_type"]
        indexes = [
            models.Index(fields=["user", "is_current"]),
            models.Index(fields=["user", "exercise", "record_type", "is_current"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "exercise", "record_type"],
                condition=models.Q(is_current=True),
                name="personal_record_one_current_per_type",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user_id}: {self.exercise_id}: {self.record_type}"
