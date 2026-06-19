import uuid

from django.conf import settings
from django.db import models


class FoodSource(models.TextChoices):
    SYSTEM = "system", "System"
    USER = "user", "User"
    EXTERNAL = "external", "External"
    AI = "ai", "AI"


class FoodDataQuality(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"


class MealType(models.TextChoices):
    BREAKFAST = "breakfast", "Breakfast"
    LUNCH = "lunch", "Lunch"
    DINNER = "dinner", "Dinner"
    SNACK = "snack", "Snack"
    CUSTOM = "custom", "Custom"


class MealItemSource(models.TextChoices):
    MANUAL = "manual", "Manual"
    AI = "ai", "AI"
    COPY = "copy", "Copy"


class FoodRecognitionStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    CONFIRMED = "confirmed", "Confirmed"
    FAILED = "failed", "Failed"


class FoodRecognitionErrorCode(models.TextChoices):
    NO_RESPONSE = "no_response", "No response"
    TIMEOUT = "timeout", "Timeout"
    INVALID_FORMAT = "invalid_format", "Invalid format"


class Food(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="foods",
    )

    source = models.CharField(
        max_length=32,
        choices=FoodSource.choices,
        default=FoodSource.USER,
    )
    external_id = models.CharField(max_length=160, blank=True)
    barcode = models.CharField(max_length=64, blank=True)

    name = models.CharField(max_length=200)
    brand = models.CharField(max_length=160, blank=True)

    serving_size = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
    )
    serving_unit = models.CharField(max_length=32, blank=True)

    calories_per_100g = models.DecimalField(max_digits=8, decimal_places=2)
    protein_per_100g = models.DecimalField(max_digits=8, decimal_places=2)
    fat_per_100g = models.DecimalField(max_digits=8, decimal_places=2)
    carbs_per_100g = models.DecimalField(max_digits=8, decimal_places=2)
    fiber_per_100g = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
    )

    data_quality = models.CharField(
        max_length=32,
        choices=FoodDataQuality.choices,
        default=FoodDataQuality.MEDIUM,
    )
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "nutrition_food"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["owner", "is_active"]),
            models.Index(fields=["source", "is_active"]),
            models.Index(fields=["name"]),
            models.Index(fields=["barcode"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(calories_per_100g__gte=0),
                name="food_calories_per_100g_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(protein_per_100g__gte=0),
                name="food_protein_per_100g_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(fat_per_100g__gte=0),
                name="food_fat_per_100g_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(carbs_per_100g__gte=0),
                name="food_carbs_per_100g_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(fiber_per_100g__isnull=True)
                | models.Q(fiber_per_100g__gte=0),
                name="food_fiber_per_100g_non_negative_or_null",
            ),
            models.CheckConstraint(
                condition=models.Q(serving_size__isnull=True)
                | models.Q(serving_size__gt=0),
                name="food_serving_size_positive_or_null",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class Meal(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="meals",
    )

    meal_date = models.DateField()
    meal_type = models.CharField(
        max_length=32,
        choices=MealType.choices,
        default=MealType.SNACK,
    )
    custom_name = models.CharField(max_length=120, blank=True)
    eaten_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    local_device_id = models.UUIDField(null=True, blank=True)
    client_updated_at = models.DateTimeField(null=True, blank=True)
    server_version = models.PositiveIntegerField(default=1)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "nutrition_meal"
        ordering = ["meal_date", "eaten_at", "created_at"]
        indexes = [
            models.Index(fields=["user", "meal_date"]),
            models.Index(fields=["user", "meal_type"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "local_device_id"],
                condition=models.Q(local_device_id__isnull=False),
                name="meal_local_device_id_unique_per_user",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user_id}: {self.meal_date}: {self.meal_type}"


class MealItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    meal = models.ForeignKey(
        Meal,
        on_delete=models.CASCADE,
        related_name="items",
    )
    food = models.ForeignKey(
        Food,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="meal_items",
    )

    display_name_snapshot = models.CharField(max_length=200)
    weight_g = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
    )
    servings = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
    )
    serving_size_snapshot = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
    )

    calories_snapshot = models.DecimalField(max_digits=10, decimal_places=2)
    protein_snapshot = models.DecimalField(max_digits=10, decimal_places=2)
    fat_snapshot = models.DecimalField(max_digits=10, decimal_places=2)
    carbs_snapshot = models.DecimalField(max_digits=10, decimal_places=2)

    source = models.CharField(
        max_length=32,
        choices=MealItemSource.choices,
        default=MealItemSource.MANUAL,
    )
    ai_recognition_item_id = models.UUIDField(null=True, blank=True)
    local_device_id = models.UUIDField(null=True, blank=True)
    client_updated_at = models.DateTimeField(null=True, blank=True)
    server_version = models.PositiveIntegerField(default=1)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "nutrition_meal_item"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["meal", "deleted_at"]),
            models.Index(fields=["food"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["meal", "local_device_id"],
                condition=models.Q(local_device_id__isnull=False),
                name="meal_item_local_device_id_unique_per_meal",
            ),
            models.CheckConstraint(
                condition=models.Q(weight_g__isnull=True) | models.Q(weight_g__gt=0),
                name="meal_item_weight_g_positive_or_null",
            ),
            models.CheckConstraint(
                condition=models.Q(servings__isnull=True) | models.Q(servings__gt=0),
                name="meal_item_servings_positive_or_null",
            ),
        ]

    def __str__(self) -> str:
        return self.display_name_snapshot


class FoodRecognition(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="food_recognitions",
    )

    image_key = models.CharField(max_length=500)
    status = models.CharField(
        max_length=32,
        choices=FoodRecognitionStatus.choices,
        default=FoodRecognitionStatus.DRAFT,
    )
    raw_ai_response = models.JSONField(null=True, blank=True)
    error_code = models.CharField(
        max_length=32,
        choices=FoodRecognitionErrorCode.choices,
        blank=True,
    )
    error_message = models.CharField(max_length=300, blank=True)

    confirmed_meal = models.ForeignKey(
        Meal,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="food_recognitions",
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "nutrition_food_recognition"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["user", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"FoodRecognition<{self.user_id}:{self.status}>"


class FoodRecognitionItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    recognition = models.ForeignKey(
        FoodRecognition,
        on_delete=models.CASCADE,
        related_name="items",
    )

    position = models.PositiveSmallIntegerField(default=0)
    ai_name = models.CharField(max_length=200)
    ai_confidence = models.DecimalField(max_digits=5, decimal_places=4)
    ai_weight_g = models.DecimalField(max_digits=8, decimal_places=2)
    ai_calories_per_100g = models.DecimalField(max_digits=8, decimal_places=2)
    ai_protein_per_100g = models.DecimalField(max_digits=8, decimal_places=2)
    ai_fat_per_100g = models.DecimalField(max_digits=8, decimal_places=2)
    ai_carbs_per_100g = models.DecimalField(max_digits=8, decimal_places=2)

    corrected_name = models.CharField(max_length=200)
    corrected_weight_g = models.DecimalField(max_digits=8, decimal_places=2)
    corrected_calories_per_100g = models.DecimalField(max_digits=8, decimal_places=2)
    corrected_protein_per_100g = models.DecimalField(max_digits=8, decimal_places=2)
    corrected_fat_per_100g = models.DecimalField(max_digits=8, decimal_places=2)
    corrected_carbs_per_100g = models.DecimalField(max_digits=8, decimal_places=2)
    user_corrected = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "nutrition_food_recognition_item"
        ordering = ["position", "created_at"]
        indexes = [
            models.Index(fields=["recognition", "position"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(ai_confidence__gte=0) & models.Q(ai_confidence__lte=1),
                name="food_recognition_item_ai_confidence_range",
            ),
            models.CheckConstraint(
                condition=models.Q(ai_weight_g__gt=0),
                name="food_recognition_item_ai_weight_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(corrected_weight_g__gt=0),
                name="food_recognition_item_corrected_weight_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(ai_calories_per_100g__gte=0)
                & models.Q(ai_protein_per_100g__gte=0)
                & models.Q(ai_fat_per_100g__gte=0)
                & models.Q(ai_carbs_per_100g__gte=0)
                & models.Q(corrected_calories_per_100g__gte=0)
                & models.Q(corrected_protein_per_100g__gte=0)
                & models.Q(corrected_fat_per_100g__gte=0)
                & models.Q(corrected_carbs_per_100g__gte=0),
                name="food_recognition_item_nutrients_non_negative",
            ),
        ]

    def __str__(self) -> str:
        return self.corrected_name
