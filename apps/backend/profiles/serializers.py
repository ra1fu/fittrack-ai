from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from profiles.models import UserGoal, UserProfile


class CurrentUserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = [
            "display_name",
            "avatar_key",
            "height_cm",
            "birth_date",
            "sex",
            "experience_level",
            "timezone",
            "locale",
            "unit_system",
            "week_starts_on",
        ]


class CurrentUserSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    email = serializers.EmailField()
    email_verified = serializers.BooleanField()


class MeSerializer(serializers.Serializer):
    user = serializers.SerializerMethodField()
    profile = serializers.SerializerMethodField()

    @extend_schema_field(CurrentUserSerializer)
    def get_user(self, user):
        return CurrentUserSerializer(user).data

    @extend_schema_field(CurrentUserProfileSerializer)
    def get_profile(self, user):
        profile = getattr(user, "profile", None)

        if profile is None:
            return None

        return CurrentUserProfileSerializer(profile).data


class UpdateProfileSerializer(serializers.Serializer):
    display_name = serializers.CharField(
        max_length=120,
        required=False,
        allow_blank=True,
    )
    height_cm = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        allow_null=True,
        min_value=1,
    )
    birth_date = serializers.DateField(
        required=False,
        allow_null=True,
    )
    sex = serializers.ChoiceField(
        choices=UserProfile._meta.get_field("sex").choices,
        required=False,
        allow_blank=True,
    )
    experience_level = serializers.ChoiceField(
        choices=UserProfile._meta.get_field("experience_level").choices,
        required=False,
    )
    timezone = serializers.CharField(
        max_length=64,
        required=False,
    )
    locale = serializers.ChoiceField(
        choices=["ru", "en"],
        required=False,
    )
    unit_system = serializers.ChoiceField(
        choices=UserProfile._meta.get_field("unit_system").choices,
        required=False,
    )
    week_starts_on = serializers.ChoiceField(
        choices=UserProfile._meta.get_field("week_starts_on").choices,
        required=False,
    )

    def validate_timezone(self, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise serializers.ValidationError("Укажите корректный часовой пояс") from exc

        return value

    def update(self, instance, validated_data):
        for field, value in validated_data.items():
            setattr(instance, field, value)

        instance.save(update_fields=[*validated_data.keys(), "updated_at"])

        return instance


class UserGoalSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserGoal
        fields = [
            "id",
            "goal_type",
            "calorie_target",
            "protein_target_g",
            "fat_target_g",
            "carbs_target_g",
            "workouts_per_week",
            "target_weight_min",
            "target_weight_max",
            "active_from",
            "active_to",
            "created_at",
            "updated_at",
        ]


class CreateUserGoalSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserGoal
        fields = [
            "goal_type",
            "calorie_target",
            "protein_target_g",
            "fat_target_g",
            "carbs_target_g",
            "workouts_per_week",
            "target_weight_min",
            "target_weight_max",
            "active_from",
            "active_to",
        ]
    
    def validate(self, attrs):
        target_weight_min = attrs.get("target_weight_min")
        target_weight_max = attrs.get("target_weight_max")
        active_from = attrs.get("active_from")
        active_to = attrs.get("active_to")

        if (
            target_weight_min is not None
            and target_weight_max is not None
            and target_weight_min > target_weight_max
        ):
            raise serializers.ValidationError(
                {
                    "target_weight_min": "Минимальный целевой вес не может быть больше максимального"
                }
            )

        if active_to is not None and active_from is not None and active_to < active_from:
            raise serializers.ValidationError(
                {
                    "active_to": "Дата окончания цели не может быть раньше даты начала"
                }
            )

        return attrs


class UpdateUserGoalSerializer(CreateUserGoalSerializer):
    pass
