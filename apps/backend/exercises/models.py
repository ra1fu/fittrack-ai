import uuid

from django.db import models
from django.conf import settings


class MuscleGroup(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    code = models.SlugField(max_length=64, unique=True)
    name = models.CharField(max_length=120)

    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="children",
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "exercises_muscle_group"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self) -> str:
        return self.name


class Equipment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    code = models.SlugField(max_length=64, unique=True)
    name = models.CharField(max_length=120)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "exercises_equipment"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self) -> str:
        return self.name


class ExerciseTrackingType(models.TextChoices):
    WEIGHT_REPS = "weight_reps", "Weight + repetitions"
    REPS_ONLY = "reps_only", "Repetitions only"
    TIME = "time", "Time"
    DISTANCE_TIME = "distance_time", "Distance + time"
    BODYWEIGHT_ADDED = "bodyweight_added", "Bodyweight + added weight"
    BODYWEIGHT_ASSISTED = "bodyweight_assisted", "Bodyweight + assistance"
    CALORIES = "calories", "Calories"
    CUSTOM = "custom", "Custom"


class Exercise(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="exercises",
    )

    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)

    primary_muscle_group = models.ForeignKey(
        MuscleGroup,
        on_delete=models.PROTECT,
        related_name="primary_exercises",
    )
    equipment = models.ForeignKey(
        Equipment,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="exercises",
    )

    tracking_type = models.CharField(
        max_length=32,
        choices=ExerciseTrackingType.choices,
        default=ExerciseTrackingType.WEIGHT_REPS,
    )

    instructions = models.TextField(blank=True)
    media_key = models.CharField(max_length=500, blank=True)

    is_system = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "exercises_exercise"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["owner", "is_active"]),
            models.Index(fields=["is_system", "is_active"]),
            models.Index(fields=["name"]),
            models.Index(fields=["tracking_type"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(is_system=True, owner__isnull=True)
                    | models.Q(is_system=False)
                ),
                name="system_exercise_has_no_owner",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(is_system=True)
                    | models.Q(is_system=False, owner__isnull=False)
                ),
                name="custom_exercise_has_owner",
            ),
        ]

    def __str__(self) -> str:
        return self.name