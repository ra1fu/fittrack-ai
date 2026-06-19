from rest_framework import serializers

from exercises.selectors import get_visible_exercises_for_user
from routines.models import Routine, RoutineDay, RoutineExercise


class RoutineExerciseSerializer(serializers.ModelSerializer):
    exercise_id = serializers.UUIDField(source="exercise.id", read_only=True)

    class Meta:
        model = RoutineExercise
        fields = [
            "id",
            "exercise_id",
            "position",
            "planned_sets",
            "rep_min",
            "rep_max",
            "target_weight",
            "target_rpe",
            "target_rir",
            "rest_seconds",
            "notes",
            "superset_group",
        ]


class CreateRoutineExerciseSerializer(serializers.Serializer):
    exercise_id = serializers.UUIDField()
    position = serializers.IntegerField(min_value=1)
    planned_sets = serializers.IntegerField(min_value=1, max_value=20, default=3)
    rep_min = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    rep_max = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    target_weight = serializers.DecimalField(
        max_digits=7,
        decimal_places=2,
        min_value=0,
        required=False,
        allow_null=True,
    )
    target_rpe = serializers.DecimalField(
        max_digits=4,
        decimal_places=2,
        min_value=1,
        max_value=10,
        required=False,
        allow_null=True,
    )
    target_rir = serializers.DecimalField(
        max_digits=4,
        decimal_places=2,
        min_value=0,
        max_value=10,
        required=False,
        allow_null=True,
    )
    rest_seconds = serializers.IntegerField(min_value=0, required=False, allow_null=True)
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
        routine_day = self.context["routine_day"]

        if routine_day.exercises.filter(position=value).exists():
            raise serializers.ValidationError("Позиция упражнения уже занята")

        return value

    def validate(self, attrs):
        rep_min = attrs.get("rep_min")
        rep_max = attrs.get("rep_max")

        if self.instance is not None:
            rep_min = attrs.get("rep_min", self.instance.rep_min)
            rep_max = attrs.get("rep_max", self.instance.rep_max)

        if rep_min is not None and rep_max is not None and rep_min > rep_max:
            raise serializers.ValidationError(
                {
                    "rep_min": "Минимум повторений не может быть больше максимума"
                }
            )

        return attrs

    def create(self, validated_data):
        exercise = validated_data.pop("exercise_id")

        return RoutineExercise.objects.create(
            routine_day=self.context["routine_day"],
            exercise=exercise,
            **validated_data,
        )


class UpdateRoutineExerciseSerializer(CreateRoutineExerciseSerializer):
    def validate_position(self, value):
        routine_day = self.context["routine_day"]
        instance = self.instance

        if routine_day.exercises.exclude(id=instance.id).filter(position=value).exists():
            raise serializers.ValidationError("Позиция упражнения уже занята")

        return value

    def update(self, instance, validated_data):
        exercise = validated_data.pop("exercise_id", None)

        if exercise is not None:
            instance.exercise = exercise

        for field, value in validated_data.items():
            setattr(instance, field, value)

        if validated_data or exercise is not None:
            update_fields = [*validated_data.keys(), "updated_at"]
            if exercise is not None:
                update_fields.append("exercise")
            instance.save(update_fields=update_fields)

        return instance


class RoutineDaySerializer(serializers.ModelSerializer):
    exercises = RoutineExerciseSerializer(many=True, read_only=True)

    class Meta:
        model = RoutineDay
        fields = [
            "id",
            "name",
            "position",
            "planned_weekday",
            "exercises",
        ]


class CreateRoutineDaySerializer(serializers.Serializer):
    name = serializers.CharField(max_length=160)
    position = serializers.IntegerField(min_value=1)
    planned_weekday = serializers.IntegerField(
        min_value=1,
        max_value=7,
        required=False,
        allow_null=True,
    )

    def validate_position(self, value):
        routine = self.context["routine"]

        if routine.days.filter(position=value).exists():
            raise serializers.ValidationError("Позиция дня уже занята")

        return value

    def create(self, validated_data):
        return RoutineDay.objects.create(
            routine=self.context["routine"],
            **validated_data,
        )


class UpdateRoutineDaySerializer(CreateRoutineDaySerializer):
    def validate_position(self, value):
        routine = self.context["routine"]
        instance = self.instance

        if routine.days.exclude(id=instance.id).filter(position=value).exists():
            raise serializers.ValidationError("Позиция дня уже занята")

        return value

    def update(self, instance, validated_data):
        for field, value in validated_data.items():
            setattr(instance, field, value)

        if validated_data:
            instance.save(update_fields=[*validated_data.keys(), "updated_at"])

        return instance


class RoutineSerializer(serializers.ModelSerializer):
    days = RoutineDaySerializer(many=True, read_only=True)

    class Meta:
        model = Routine
        fields = [
            "id",
            "name",
            "description",
            "color",
            "is_active",
            "version",
            "days",
            "created_at",
            "updated_at",
        ]


class EmptyMetaSerializer(serializers.Serializer):
    pass


class RoutineSuccessDataSerializer(serializers.Serializer):
    success = serializers.BooleanField()


class RoutineListMetaSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    total_count = serializers.IntegerField()
    limit = serializers.IntegerField()
    offset = serializers.IntegerField()


class RoutineListResponseSerializer(serializers.Serializer):
    data = RoutineSerializer(many=True)
    meta = RoutineListMetaSerializer()


class RoutineResponseSerializer(serializers.Serializer):
    data = RoutineSerializer()
    meta = EmptyMetaSerializer()


class RoutineDayResponseSerializer(serializers.Serializer):
    data = RoutineDaySerializer()
    meta = EmptyMetaSerializer()


class RoutineExerciseResponseSerializer(serializers.Serializer):
    data = RoutineExerciseSerializer()
    meta = EmptyMetaSerializer()


class RoutineSuccessResponseSerializer(serializers.Serializer):
    data = RoutineSuccessDataSerializer()
    meta = EmptyMetaSerializer()


class CreateRoutineSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=160)
    description = serializers.CharField(required=False, allow_blank=True)
    color = serializers.CharField(max_length=32, required=False, allow_blank=True)

    def create(self, validated_data):
        return Routine.objects.create(
            user=self.context["request"].user,
            **validated_data,
        )


class UpdateRoutineSerializer(CreateRoutineSerializer):
    def update(self, instance, validated_data):
        for field, value in validated_data.items():
            setattr(instance, field, value)

        if validated_data:
            instance.version += 1
            instance.save(update_fields=[*validated_data.keys(), "version", "updated_at"])

        return instance
