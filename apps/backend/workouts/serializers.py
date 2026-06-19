from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from django.utils import timezone

from exercises.selectors import get_visible_exercises_for_user
from workouts.calculations import calculate_workout_metrics
from workouts.models import (
    PersonalRecord,
    Workout,
    WorkoutExercise,
    WorkoutSet,
    WorkoutSetType,
)
from workouts.services import StartWorkoutCommand, start_workout


class WorkoutSetSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkoutSet
        fields = [
            "id",
            "position",
            "set_type",
            "weight",
            "repetitions",
            "duration_seconds",
            "distance_meters",
            "rpe",
            "rir",
            "is_completed",
            "completed_at",
            "notes",
        ]


class WorkoutExerciseSerializer(serializers.ModelSerializer):
    exercise_id = serializers.UUIDField(source="exercise.id", read_only=True)
    source_routine_exercise_id = serializers.UUIDField(
        source="source_routine_exercise.id",
        read_only=True,
    )
    sets = WorkoutSetSerializer(many=True, read_only=True)

    class Meta:
        model = WorkoutExercise
        fields = [
            "id",
            "exercise_id",
            "source_routine_exercise_id",
            "position",
            "notes",
            "superset_group",
            "sets",
        ]


class WorkoutSerializer(serializers.ModelSerializer):
    source_routine_id = serializers.SerializerMethodField()
    source_routine_day_id = serializers.SerializerMethodField()
    metrics = serializers.SerializerMethodField()
    exercises = WorkoutExerciseSerializer(many=True, read_only=True)

    class Meta:
        model = Workout
        fields = [
            "id",
            "source_routine_id",
            "source_routine_day_id",
            "name",
            "status",
            "started_at",
            "finished_at",
            "duration_seconds",
            "notes",
            "local_device_id",
            "client_updated_at",
            "server_version",
            "metrics",
            "exercises",
            "created_at",
            "updated_at",
        ]

    @extend_schema_field(OpenApiTypes.UUID)
    def get_source_routine_id(self, obj):
        if obj.source_routine_id is None:
            return None

        return obj.source_routine_id

    @extend_schema_field(OpenApiTypes.UUID)
    def get_source_routine_day_id(self, obj):
        if obj.source_routine_day_id is None:
            return None

        return obj.source_routine_day_id

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_metrics(self, obj):
        return calculate_workout_metrics(obj)


class PersonalRecordSerializer(serializers.ModelSerializer):
    exercise_id = serializers.UUIDField(source="exercise.id", read_only=True)
    workout_set_id = serializers.UUIDField(source="workout_set.id", read_only=True)

    class Meta:
        model = PersonalRecord
        fields = [
            "id",
            "exercise_id",
            "workout_set_id",
            "record_type",
            "value",
            "unit",
            "achieved_at",
            "is_current",
        ]


class EmptyMetaSerializer(serializers.Serializer):
    pass


class WorkoutCountMetaSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    total_count = serializers.IntegerField()
    limit = serializers.IntegerField()
    offset = serializers.IntegerField()


class WorkoutSuccessDataSerializer(serializers.Serializer):
    success = serializers.BooleanField()


class WorkoutListResponseSerializer(serializers.Serializer):
    data = WorkoutSerializer(many=True)
    meta = WorkoutCountMetaSerializer()


class WorkoutResponseSerializer(serializers.Serializer):
    data = WorkoutSerializer(allow_null=True)
    meta = EmptyMetaSerializer()


class WorkoutSetResponseSerializer(serializers.Serializer):
    data = WorkoutSetSerializer()
    meta = EmptyMetaSerializer()


class PersonalRecordListResponseSerializer(serializers.Serializer):
    data = PersonalRecordSerializer(many=True)
    meta = WorkoutCountMetaSerializer()


class WorkoutSuccessResponseSerializer(serializers.Serializer):
    data = WorkoutSuccessDataSerializer()
    meta = EmptyMetaSerializer()


class WorkoutExerciseResponseSerializer(serializers.Serializer):
    data = WorkoutExerciseSerializer()
    meta = EmptyMetaSerializer()


class StartWorkoutSerializer(serializers.Serializer):
    source_routine_day_id = serializers.UUIDField(required=False, allow_null=True)
    name = serializers.CharField(max_length=160, required=False, allow_blank=True)
    started_at = serializers.DateTimeField(required=False)
    notes = serializers.CharField(required=False, allow_blank=True)
    local_device_id = serializers.UUIDField(required=False, allow_null=True)
    client_updated_at = serializers.DateTimeField(required=False, allow_null=True)

    def validate_name(self, value):
        if value == "":
            return None

        return value

    def create(self, validated_data):
        command = StartWorkoutCommand(
            user_id=self.context["request"].user.id,
            source_routine_day_id=validated_data.get("source_routine_day_id"),
            name=validated_data.get("name"),
            started_at=validated_data.get("started_at"),
            notes=validated_data.get("notes", ""),
            local_device_id=validated_data.get("local_device_id"),
            client_updated_at=validated_data.get("client_updated_at"),
        )

        return start_workout(
            user=self.context["request"].user,
            command=command,
        )


class CreateWorkoutExerciseSerializer(serializers.Serializer):
    exercise_id = serializers.UUIDField()
    position = serializers.IntegerField(min_value=1)
    notes = serializers.CharField(required=False, allow_blank=True)
    superset_group = serializers.CharField(
        max_length=32,
        required=False,
        allow_blank=True,
    )

    def validate_exercise_id(self, value):
        user = self.context["request"].user
        visible_exercises = get_visible_exercises_for_user(user)

        try:
            return visible_exercises.get(id=value)
        except visible_exercises.model.DoesNotExist as exc:
            raise serializers.ValidationError("Упражнение не найдено") from exc

    def validate_position(self, value):
        workout = self.context["workout"]

        if workout.exercises.filter(position=value).exists():
            raise serializers.ValidationError("Позиция упражнения уже занята")

        return value

    def create(self, validated_data):
        exercise = validated_data.pop("exercise_id")

        return WorkoutExercise.objects.create(
            workout=self.context["workout"],
            exercise=exercise,
            **validated_data,
        )


class CreateWorkoutSetSerializer(serializers.Serializer):
    position = serializers.IntegerField(min_value=1)
    set_type = serializers.ChoiceField(
        choices=WorkoutSetType.choices,
        default=WorkoutSetType.WORKING,
    )
    weight = serializers.DecimalField(
        max_digits=7,
        decimal_places=2,
        min_value=0,
        required=False,
        allow_null=True,
    )
    repetitions = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    duration_seconds = serializers.IntegerField(
        min_value=0,
        required=False,
        allow_null=True,
    )
    distance_meters = serializers.DecimalField(
        max_digits=9,
        decimal_places=2,
        min_value=0,
        required=False,
        allow_null=True,
    )
    rpe = serializers.DecimalField(
        max_digits=4,
        decimal_places=2,
        min_value=1,
        max_value=10,
        required=False,
        allow_null=True,
    )
    rir = serializers.DecimalField(
        max_digits=4,
        decimal_places=2,
        min_value=0,
        max_value=10,
        required=False,
        allow_null=True,
    )
    is_completed = serializers.BooleanField(required=False, default=False)
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate_position(self, value):
        workout_exercise = self.context["workout_exercise"]

        if workout_exercise.sets.filter(position=value, deleted_at__isnull=True).exists():
            raise serializers.ValidationError("Позиция подхода уже занята")

        return value

    def create(self, validated_data):
        if validated_data.get("is_completed") is True:
            validated_data["completed_at"] = timezone.now()

        return WorkoutSet.objects.create(
            workout_exercise=self.context["workout_exercise"],
            **validated_data,
        )


class UpdateWorkoutSetSerializer(CreateWorkoutSetSerializer):
    position = serializers.IntegerField(min_value=1, required=False)
    set_type = serializers.ChoiceField(
        choices=WorkoutSetType.choices,
        required=False,
    )
    is_completed = serializers.BooleanField(required=False)

    def validate_position(self, value):
        workout_exercise = self.context["workout_exercise"]
        instance = self.instance

        if (
            workout_exercise.sets.exclude(id=instance.id)
            .filter(position=value, deleted_at__isnull=True)
            .exists()
        ):
            raise serializers.ValidationError("Позиция подхода уже занята")

        return value

    def update(self, instance, validated_data):
        if "is_completed" in validated_data:
            if validated_data["is_completed"] is True and instance.completed_at is None:
                validated_data["completed_at"] = timezone.now()
            elif validated_data["is_completed"] is False:
                validated_data["completed_at"] = None

        for field, value in validated_data.items():
            setattr(instance, field, value)

        if validated_data:
            instance.save(update_fields=[*validated_data.keys(), "updated_at"])

        return instance
