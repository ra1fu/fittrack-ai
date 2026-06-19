from decimal import Decimal

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from django.conf import settings

from nutrition.calculations import (
    calculate_nutrients_from_per_100g,
    calculate_nutrients_for_servings,
    calculate_nutrients_for_weight,
)
from nutrition.models import (
    Food,
    FoodRecognition,
    FoodRecognitionItem,
    FoodSource,
    Meal,
    MealItem,
    MealItemSource,
)
from nutrition.selectors import get_visible_foods_for_user


class FoodSerializer(serializers.ModelSerializer):
    owner_id = serializers.UUIDField(source="owner.id", read_only=True)

    class Meta:
        model = Food
        fields = [
            "id",
            "owner_id",
            "source",
            "external_id",
            "barcode",
            "name",
            "brand",
            "serving_size",
            "serving_unit",
            "calories_per_100g",
            "protein_per_100g",
            "fat_per_100g",
            "carbs_per_100g",
            "fiber_per_100g",
            "data_quality",
            "is_verified",
        ]


class FoodQuerySerializer(serializers.Serializer):
    search = serializers.CharField(required=False, allow_blank=True)
    barcode = serializers.CharField(required=False, allow_blank=True)
    source = serializers.ChoiceField(
        choices=FoodSource.choices,
        required=False,
    )
    is_verified = serializers.BooleanField(required=False)
    limit = serializers.IntegerField(
        required=False,
        default=50,
        min_value=1,
        max_value=100,
    )
    offset = serializers.IntegerField(
        required=False,
        default=0,
        min_value=0,
    )


class CreateFoodSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    brand = serializers.CharField(max_length=160, required=False, allow_blank=True)
    serving_size = serializers.DecimalField(
        max_digits=8,
        decimal_places=2,
        min_value=Decimal("0.01"),
        required=False,
        allow_null=True,
    )
    serving_unit = serializers.CharField(max_length=32, required=False, allow_blank=True)
    calories_per_100g = serializers.DecimalField(
        max_digits=8,
        decimal_places=2,
        min_value=0,
    )
    protein_per_100g = serializers.DecimalField(
        max_digits=8,
        decimal_places=2,
        min_value=0,
    )
    fat_per_100g = serializers.DecimalField(
        max_digits=8,
        decimal_places=2,
        min_value=0,
    )
    carbs_per_100g = serializers.DecimalField(
        max_digits=8,
        decimal_places=2,
        min_value=0,
    )
    fiber_per_100g = serializers.DecimalField(
        max_digits=8,
        decimal_places=2,
        min_value=0,
        required=False,
        allow_null=True,
    )
    barcode = serializers.CharField(max_length=64, required=False, allow_blank=True)

    def validate_barcode(self, value):
        return value.strip()

    def validate(self, attrs):
        barcode = attrs.get("barcode", "")

        if barcode and Food.objects.filter(
            owner=self.context["request"].user,
            barcode=barcode,
            is_active=True,
        ).exists():
            raise serializers.ValidationError(
                {
                    "barcode": "Продукт с таким штрихкодом уже есть в вашем каталоге"
                }
            )

        return attrs

    def create(self, validated_data):
        return Food.objects.create(
            owner=self.context["request"].user,
            source=FoodSource.USER,
            **validated_data,
        )


class UpdateFoodSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200, required=False)
    brand = serializers.CharField(max_length=160, required=False, allow_blank=True)
    serving_size = serializers.DecimalField(
        max_digits=8,
        decimal_places=2,
        min_value=Decimal("0.01"),
        required=False,
        allow_null=True,
    )
    serving_unit = serializers.CharField(max_length=32, required=False, allow_blank=True)
    calories_per_100g = serializers.DecimalField(
        max_digits=8,
        decimal_places=2,
        min_value=0,
        required=False,
    )
    protein_per_100g = serializers.DecimalField(
        max_digits=8,
        decimal_places=2,
        min_value=0,
        required=False,
    )
    fat_per_100g = serializers.DecimalField(
        max_digits=8,
        decimal_places=2,
        min_value=0,
        required=False,
    )
    carbs_per_100g = serializers.DecimalField(
        max_digits=8,
        decimal_places=2,
        min_value=0,
        required=False,
    )
    fiber_per_100g = serializers.DecimalField(
        max_digits=8,
        decimal_places=2,
        min_value=0,
        required=False,
        allow_null=True,
    )
    barcode = serializers.CharField(max_length=64, required=False, allow_blank=True)

    def validate_barcode(self, value):
        return value.strip()

    def validate(self, attrs):
        barcode = attrs.get("barcode")

        if barcode and Food.objects.filter(
            owner=self.context["request"].user,
            barcode=barcode,
            is_active=True,
        ).exclude(id=self.instance.id).exists():
            raise serializers.ValidationError(
                {
                    "barcode": "Продукт с таким штрихкодом уже есть в вашем каталоге"
                }
            )

        return attrs

    def update(self, instance, validated_data):
        for field, value in validated_data.items():
            setattr(instance, field, value)

        instance.save(update_fields=[*validated_data.keys(), "updated_at"])

        return instance


class MealItemSerializer(serializers.ModelSerializer):
    food_id = serializers.UUIDField(source="food.id", read_only=True)

    class Meta:
        model = MealItem
        fields = [
            "id",
            "food_id",
            "display_name_snapshot",
            "weight_g",
            "servings",
            "serving_size_snapshot",
            "calories_snapshot",
            "protein_snapshot",
            "fat_snapshot",
            "carbs_snapshot",
            "source",
            "local_device_id",
            "client_updated_at",
            "server_version",
            "created_at",
        ]


class MealSerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()
    totals = serializers.SerializerMethodField()

    class Meta:
        model = Meal
        fields = [
            "id",
            "meal_date",
            "meal_type",
            "custom_name",
            "eaten_at",
            "notes",
            "local_device_id",
            "client_updated_at",
            "server_version",
            "items",
            "totals",
        ]

    @extend_schema_field(MealItemSerializer(many=True))
    def get_items(self, obj):
        items = obj.items.filter(deleted_at__isnull=True)
        return MealItemSerializer(items, many=True).data

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_totals(self, obj):
        items = obj.items.filter(deleted_at__isnull=True)
        return calculate_meal_item_totals(items)


class FoodRecognitionItemSerializer(serializers.ModelSerializer):
    totals = serializers.SerializerMethodField()

    class Meta:
        model = FoodRecognitionItem
        fields = [
            "id",
            "position",
            "ai_name",
            "ai_confidence",
            "ai_weight_g",
            "ai_calories_per_100g",
            "ai_protein_per_100g",
            "ai_fat_per_100g",
            "ai_carbs_per_100g",
            "corrected_name",
            "corrected_weight_g",
            "corrected_calories_per_100g",
            "corrected_protein_per_100g",
            "corrected_fat_per_100g",
            "corrected_carbs_per_100g",
            "user_corrected",
            "totals",
            "created_at",
            "updated_at",
        ]

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_totals(self, obj):
        nutrients = calculate_nutrients_from_per_100g(
            calories_per_100g=obj.corrected_calories_per_100g,
            protein_per_100g=obj.corrected_protein_per_100g,
            fat_per_100g=obj.corrected_fat_per_100g,
            carbs_per_100g=obj.corrected_carbs_per_100g,
            weight_g=obj.corrected_weight_g,
        )

        return {
            key: f"{value:.2f}"
            for key, value in nutrients.items()
        }


class FoodRecognitionSerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()
    confirmed_meal_id = serializers.UUIDField(source="confirmed_meal.id", read_only=True)

    class Meta:
        model = FoodRecognition
        fields = [
            "id",
            "image_key",
            "status",
            "raw_ai_response",
            "error_code",
            "error_message",
            "confirmed_meal_id",
            "confirmed_at",
            "items",
            "created_at",
            "updated_at",
        ]

    @extend_schema_field(FoodRecognitionItemSerializer(many=True))
    def get_items(self, obj):
        items = obj.items.order_by("position", "created_at")
        return FoodRecognitionItemSerializer(items, many=True).data


class EmptyMetaSerializer(serializers.Serializer):
    pass


class NutritionCountMetaSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    total_count = serializers.IntegerField()
    limit = serializers.IntegerField()
    offset = serializers.IntegerField()


class FoodListMetaSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    total_count = serializers.IntegerField()
    limit = serializers.IntegerField()
    offset = serializers.IntegerField()


class NutritionSuccessDataSerializer(serializers.Serializer):
    success = serializers.BooleanField()


class NutrientTotalsSerializer(serializers.Serializer):
    calories = serializers.CharField()
    protein = serializers.CharField()
    fat = serializers.CharField()
    carbs = serializers.CharField()


class NutritionDayTargetsSerializer(serializers.Serializer):
    active_goal_id = serializers.UUIDField(allow_null=True)
    goal_type = serializers.CharField(allow_null=True)
    calories = serializers.CharField(allow_null=True)
    protein = serializers.CharField(allow_null=True)
    fat = serializers.CharField(allow_null=True)
    carbs = serializers.CharField(allow_null=True)


class NutritionDayProgressItemSerializer(serializers.Serializer):
    consumed = serializers.CharField()
    target = serializers.CharField(allow_null=True)
    remaining = serializers.CharField(allow_null=True)
    percent = serializers.CharField(allow_null=True)


class NutritionDayProgressSerializer(serializers.Serializer):
    calories = NutritionDayProgressItemSerializer()
    protein = NutritionDayProgressItemSerializer()
    fat = NutritionDayProgressItemSerializer()
    carbs = NutritionDayProgressItemSerializer()


class FoodListResponseSerializer(serializers.Serializer):
    data = FoodSerializer(many=True)
    meta = FoodListMetaSerializer()


class FoodResponseSerializer(serializers.Serializer):
    data = FoodSerializer()
    meta = EmptyMetaSerializer()


class FoodRecognitionListResponseSerializer(serializers.Serializer):
    data = FoodRecognitionSerializer(many=True)
    meta = NutritionCountMetaSerializer()


class FoodRecognitionResponseSerializer(serializers.Serializer):
    data = FoodRecognitionSerializer()
    meta = EmptyMetaSerializer()


class FoodRecognitionItemResponseSerializer(serializers.Serializer):
    data = FoodRecognitionItemSerializer()
    meta = EmptyMetaSerializer()


class MealListResponseSerializer(serializers.Serializer):
    data = MealSerializer(many=True)
    meta = NutritionCountMetaSerializer()


class MealResponseSerializer(serializers.Serializer):
    data = MealSerializer()
    meta = EmptyMetaSerializer()


class MealItemResponseSerializer(serializers.Serializer):
    data = MealItemSerializer()
    meta = EmptyMetaSerializer()


class NutritionDayDataSerializer(serializers.Serializer):
    date = serializers.DateField()
    totals = NutrientTotalsSerializer()
    targets = NutritionDayTargetsSerializer()
    progress = NutritionDayProgressSerializer()
    meals = MealSerializer(many=True)


class NutritionDayResponseSerializer(serializers.Serializer):
    data = NutritionDayDataSerializer()
    meta = EmptyMetaSerializer()


class NutritionSuccessResponseSerializer(serializers.Serializer):
    data = NutritionSuccessDataSerializer()
    meta = EmptyMetaSerializer()


class CreateFoodRecognitionSerializer(serializers.Serializer):
    image_key = serializers.CharField(max_length=500)
    raw_ai_response = serializers.JSONField(required=False, allow_null=True)


class UploadFoodRecognitionPhotoSerializer(serializers.Serializer):
    image = serializers.FileField()
    raw_ai_response = serializers.CharField(required=False, allow_blank=True)

    def validate_image(self, value):
        allowed_content_types = settings.NUTRITION_AI_PHOTO_ALLOWED_CONTENT_TYPES

        if value.content_type not in allowed_content_types:
            raise serializers.ValidationError("Поддерживаются только JPEG, PNG или WEBP")

        if value.size > settings.NUTRITION_AI_PHOTO_MAX_BYTES:
            raise serializers.ValidationError("Файл слишком большой")

        return value


class UpdateFoodRecognitionItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = FoodRecognitionItem
        fields = [
            "corrected_name",
            "corrected_weight_g",
            "corrected_calories_per_100g",
            "corrected_protein_per_100g",
            "corrected_fat_per_100g",
            "corrected_carbs_per_100g",
        ]
        extra_kwargs = {
            "corrected_name": {
                "required": False,
                "allow_blank": False,
            },
            "corrected_weight_g": {
                "required": False,
                "min_value": Decimal("0.01"),
            },
            "corrected_calories_per_100g": {
                "required": False,
                "min_value": Decimal("0"),
            },
            "corrected_protein_per_100g": {
                "required": False,
                "min_value": Decimal("0"),
            },
            "corrected_fat_per_100g": {
                "required": False,
                "min_value": Decimal("0"),
            },
            "corrected_carbs_per_100g": {
                "required": False,
                "min_value": Decimal("0"),
            },
        }

    def update(self, instance, validated_data):
        for field, value in validated_data.items():
            setattr(instance, field, value)

        instance.user_corrected = True
        instance.save(update_fields=[*validated_data.keys(), "user_corrected", "updated_at"])

        return instance


class ConfirmFoodRecognitionSerializer(serializers.Serializer):
    meal_id = serializers.UUIDField(required=False)
    meal_date = serializers.DateField(required=False)
    meal_type = serializers.ChoiceField(
        choices=Meal._meta.get_field("meal_type").choices,
        required=False,
    )
    custom_name = serializers.CharField(max_length=120, required=False, allow_blank=True)
    eaten_at = serializers.DateTimeField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        meal_id = attrs.get("meal_id")

        if meal_id:
            return attrs

        if attrs.get("meal_date") is None:
            raise serializers.ValidationError(
                {
                    "meal_date": "Укажите дату приёма пищи"
                }
            )

        if attrs.get("meal_type") is None:
            raise serializers.ValidationError(
                {
                    "meal_type": "Укажите тип приёма пищи"
                }
            )

        return attrs


class CreateMealSerializer(serializers.Serializer):
    meal_date = serializers.DateField()
    meal_type = serializers.ChoiceField(choices=Meal._meta.get_field("meal_type").choices)
    custom_name = serializers.CharField(max_length=120, required=False, allow_blank=True)
    eaten_at = serializers.DateTimeField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    local_device_id = serializers.UUIDField(required=False, allow_null=True)
    client_updated_at = serializers.DateTimeField(required=False, allow_null=True)

    def create(self, validated_data):
        local_device_id = validated_data.get("local_device_id")
        if local_device_id is not None:
            existing_meal = Meal.objects.filter(
                user=self.context["request"].user,
                local_device_id=local_device_id,
            ).first()

            if existing_meal is not None:
                return existing_meal

        return Meal.objects.create(
            user=self.context["request"].user,
            **validated_data,
        )


class UpdateMealSerializer(serializers.ModelSerializer):
    class Meta:
        model = Meal
        fields = [
            "meal_date",
            "meal_type",
            "custom_name",
            "eaten_at",
            "notes",
            "client_updated_at",
        ]

    def update(self, instance, validated_data):
        for field, value in validated_data.items():
            setattr(instance, field, value)

        instance.server_version += 1
        instance.save(update_fields=[*validated_data.keys(), "server_version", "updated_at"])

        return instance


class CreateMealItemSerializer(serializers.Serializer):
    food_id = serializers.UUIDField()
    weight_g = serializers.DecimalField(
        max_digits=8,
        decimal_places=2,
        min_value=Decimal("0.01"),
        required=False,
        allow_null=True,
    )
    servings = serializers.DecimalField(
        max_digits=8,
        decimal_places=2,
        min_value=Decimal("0.01"),
        required=False,
        allow_null=True,
    )
    local_device_id = serializers.UUIDField(required=False, allow_null=True)
    client_updated_at = serializers.DateTimeField(required=False, allow_null=True)

    def validate_food_id(self, value):
        visible_foods = get_visible_foods_for_user(self.context["request"].user)

        try:
            return visible_foods.get(id=value)
        except visible_foods.model.DoesNotExist as exc:
            raise serializers.ValidationError("Продукт не найден") from exc

    def validate(self, attrs):
        weight_g = attrs.get("weight_g")
        servings = attrs.get("servings")

        if weight_g is None and servings is None:
            raise serializers.ValidationError(
                {
                    "weight_g": "Укажите массу или количество порций"
                }
            )

        if weight_g is not None and servings is not None:
            raise serializers.ValidationError(
                {
                    "servings": "Укажите либо массу, либо количество порций"
                }
            )

        food = attrs["food_id"]
        if servings is not None and food.serving_size is None:
            raise serializers.ValidationError(
                {
                    "servings": "Для продукта не задан размер порции"
                }
            )

        return attrs

    def create(self, validated_data):
        local_device_id = validated_data.get("local_device_id")
        if local_device_id is not None:
            existing_item = MealItem.objects.filter(
                meal=self.context["meal"],
                local_device_id=local_device_id,
                deleted_at__isnull=True,
            ).first()

            if existing_item is not None:
                return existing_item

        food = validated_data.pop("food_id")
        weight_g = validated_data.get("weight_g")
        servings = validated_data.get("servings")
        client_updated_at = validated_data.get("client_updated_at")

        if weight_g is not None:
            nutrients = calculate_nutrients_for_weight(food, weight_g)
        else:
            nutrients = calculate_nutrients_for_servings(food, servings)

        return MealItem.objects.create(
            meal=self.context["meal"],
            food=food,
            display_name_snapshot=food.name,
            weight_g=weight_g,
            servings=servings,
            serving_size_snapshot=food.serving_size,
            calories_snapshot=nutrients["calories"],
            protein_snapshot=nutrients["protein"],
            fat_snapshot=nutrients["fat"],
            carbs_snapshot=nutrients["carbs"],
            source=MealItemSource.MANUAL,
            local_device_id=local_device_id,
            client_updated_at=client_updated_at,
        )


class UpdateMealItemSerializer(serializers.Serializer):
    food_id = serializers.UUIDField(required=False)
    weight_g = serializers.DecimalField(
        max_digits=8,
        decimal_places=2,
        min_value=Decimal("0.01"),
        required=False,
        allow_null=True,
    )
    servings = serializers.DecimalField(
        max_digits=8,
        decimal_places=2,
        min_value=Decimal("0.01"),
        required=False,
        allow_null=True,
    )
    client_updated_at = serializers.DateTimeField(required=False, allow_null=True)

    def validate_food_id(self, value):
        visible_foods = get_visible_foods_for_user(self.context["request"].user)

        try:
            return visible_foods.get(id=value)
        except visible_foods.model.DoesNotExist as exc:
            raise serializers.ValidationError("Продукт не найден") from exc

    def validate(self, attrs):
        meal_item = self.context["meal_item"]
        food = attrs.get("food_id", meal_item.food)
        weight_g = attrs.get("weight_g", meal_item.weight_g)
        servings = attrs.get("servings", meal_item.servings)

        if food is None:
            raise serializers.ValidationError(
                {
                    "food_id": "Укажите продукт для пересчёта"
                }
            )

        if weight_g is None and servings is None:
            raise serializers.ValidationError(
                {
                    "weight_g": "Укажите массу или количество порций"
                }
            )

        if weight_g is not None and servings is not None:
            raise serializers.ValidationError(
                {
                    "servings": "Укажите либо массу, либо количество порций"
                }
            )

        if servings is not None and food.serving_size is None:
            raise serializers.ValidationError(
                {
                    "servings": "Для продукта не задан размер порции"
                }
            )

        attrs["resolved_food"] = food
        attrs["resolved_weight_g"] = weight_g
        attrs["resolved_servings"] = servings

        return attrs

    def update(self, instance, validated_data):
        food = validated_data["resolved_food"]
        weight_g = validated_data["resolved_weight_g"]
        servings = validated_data["resolved_servings"]

        if weight_g is not None:
            nutrients = calculate_nutrients_for_weight(food, weight_g)
        else:
            nutrients = calculate_nutrients_for_servings(food, servings)

        instance.food = food
        instance.display_name_snapshot = food.name
        instance.weight_g = weight_g
        instance.servings = servings
        instance.serving_size_snapshot = food.serving_size
        instance.calories_snapshot = nutrients["calories"]
        instance.protein_snapshot = nutrients["protein"]
        instance.fat_snapshot = nutrients["fat"]
        instance.carbs_snapshot = nutrients["carbs"]
        if "client_updated_at" in validated_data:
            instance.client_updated_at = validated_data["client_updated_at"]
        instance.server_version += 1
        instance.save(
            update_fields=[
                "food",
                "display_name_snapshot",
                "weight_g",
                "servings",
                "serving_size_snapshot",
                "calories_snapshot",
                "protein_snapshot",
                "fat_snapshot",
                "carbs_snapshot",
                "client_updated_at",
                "server_version",
                "updated_at",
            ]
        )

        return instance


def calculate_meal_item_totals(items) -> dict:
    totals = {
        "calories": Decimal("0.00"),
        "protein": Decimal("0.00"),
        "fat": Decimal("0.00"),
        "carbs": Decimal("0.00"),
    }

    for item in items:
        totals["calories"] += item.calories_snapshot
        totals["protein"] += item.protein_snapshot
        totals["fat"] += item.fat_snapshot
        totals["carbs"] += item.carbs_snapshot

    return {
        key: f"{value:.2f}"
        for key, value in totals.items()
    }
