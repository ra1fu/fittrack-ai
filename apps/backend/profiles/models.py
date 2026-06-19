import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q


class ExperienceLevel(models.TextChoices):
    BEGINNER = "beginner", "Beginner"
    INTERMEDIATE = "intermediate", "Intermediate"
    ADVANCED = "advanced", "Advanced"


class UnitSystem(models.TextChoices):
    METRIC = "metric", "Metric"
    IMPERIAL = "imperial", "Imperial"


class Weekday(models.TextChoices):
    MONDAY = "monday", "Monday"
    SUNDAY = "sunday", "Sunday"


class Sex(models.TextChoices):
    MALE = "male", "Male"
    FEMALE = "female", "Female"
    OTHER = "other", "Other"
    PREFER_NOT_TO_SAY = "prefer_not_to_say", "Prefer not to say"


class GoalType(models.TextChoices):
    MAINTENANCE = "maintenance", "Maintenance"
    STRENGTH = "strength", "Strength"
    MUSCLE_GAIN = "muscle_gain", "Muscle gain"
    GRADUAL_WEIGHT_LOSS = "gradual_weight_loss", "Gradual weight loss"
    REGULARITY = "regularity", "Regularity"
    CUSTOM = "custom", "Custom"


class UserProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )

    display_name = models.CharField(max_length=120, blank=True)
    avatar_key = models.CharField(max_length=500, blank=True)

    height_cm = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )
    birth_date = models.DateField(null=True, blank=True)
    sex = models.CharField(
        max_length=32,
        choices=Sex.choices,
        blank=True,
    )

    experience_level = models.CharField(
        max_length=32,
        choices=ExperienceLevel.choices,
        default=ExperienceLevel.BEGINNER,
    )
    timezone = models.CharField(max_length=64, default="UTC")
    locale = models.CharField(max_length=16, default="ru")
    unit_system = models.CharField(
        max_length=16,
        choices=UnitSystem.choices,
        default=UnitSystem.METRIC,
    )
    week_starts_on = models.CharField(
        max_length=16,
        choices=Weekday.choices,
        default=Weekday.MONDAY,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "profiles_user_profile"
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["locale"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(height_cm__isnull=True) | Q(height_cm__gt=0),
                name="profile_height_cm_positive_or_null",
            ),
        ]

    def __str__(self) -> str:
        return f"Profile<{self.user_id}>"


class UserGoal(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="goals",
    )

    goal_type = models.CharField(
        max_length=32,
        choices=GoalType.choices,
        default=GoalType.MAINTENANCE,
    )

    calorie_target = models.PositiveIntegerField(null=True, blank=True)
    protein_target_g = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
    )
    fat_target_g = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
    )
    carbs_target_g = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
    )

    workouts_per_week = models.PositiveSmallIntegerField(null=True, blank=True)

    target_weight_min = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
    )
    target_weight_max = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
    )

    active_from = models.DateField()
    active_to = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "profiles_user_goal"
        indexes = [
            models.Index(fields=["user", "active_from"]),
            models.Index(fields=["user", "active_to"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(calorie_target__isnull=True) | Q(calorie_target__gte=1),
                name="goal_calorie_target_positive_or_null",
            ),
            models.CheckConstraint(
                condition=Q(protein_target_g__isnull=True) | Q(protein_target_g__gte=0),
                name="goal_protein_target_non_negative_or_null",
            ),
            models.CheckConstraint(
                condition=Q(fat_target_g__isnull=True) | Q(fat_target_g__gte=0),
                name="goal_fat_target_non_negative_or_null",
            ),
            models.CheckConstraint(
                condition=Q(carbs_target_g__isnull=True) | Q(carbs_target_g__gte=0),
                name="goal_carbs_target_non_negative_or_null",
            ),
            models.CheckConstraint(
                condition=Q(workouts_per_week__isnull=True)
                | (Q(workouts_per_week__gte=0) & Q(workouts_per_week__lte=14)),
                name="goal_workouts_per_week_reasonable_or_null",
            ),
            models.CheckConstraint(
                condition=Q(target_weight_min__isnull=True) | Q(target_weight_min__gt=0),
                name="goal_target_weight_min_positive_or_null",
            ),
            models.CheckConstraint(
                condition=Q(target_weight_max__isnull=True) | Q(target_weight_max__gt=0),
                name="goal_target_weight_max_positive_or_null",
            ),
            models.CheckConstraint(
                condition=Q(target_weight_min__isnull=True)
                | Q(target_weight_max__isnull=True)
                | Q(target_weight_min__lte=models.F("target_weight_max")),
                name="goal_target_weight_range_valid",
            ),
            models.CheckConstraint(
                condition=Q(active_to__isnull=True) | Q(active_to__gte=models.F("active_from")),
                name="goal_active_period_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"Goal<{self.user_id}:{self.goal_type}>"