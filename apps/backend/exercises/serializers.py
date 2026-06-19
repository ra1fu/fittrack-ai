from rest_framework import serializers

from exercises.models import Equipment, Exercise, MuscleGroup


class MuscleGroupSerializer(serializers.ModelSerializer):
    parent_id = serializers.UUIDField(source="parent.id", read_only=True)

    class Meta:
        model = MuscleGroup
        fields = [
            "id",
            "code",
            "name",
            "parent_id",
        ]


class EquipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Equipment
        fields = [
            "id",
            "code",
            "name",
        ]


class ExerciseSerializer(serializers.ModelSerializer):
    primary_muscle_group = MuscleGroupSerializer(read_only=True)
    equipment = EquipmentSerializer(read_only=True)
    owner_id = serializers.UUIDField(source="owner.id", read_only=True)

    class Meta:
        model = Exercise
        fields = [
            "id",
            "owner_id",
            "name",
            "description",
            "primary_muscle_group",
            "equipment",
            "tracking_type",
            "instructions",
            "media_key",
            "is_system",
        ]


class CreateExerciseSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=160)
    description = serializers.CharField(required=False, allow_blank=True)
    primary_muscle_group_id = serializers.UUIDField()
    equipment_id = serializers.UUIDField(required=False, allow_null=True)
    tracking_type = serializers.ChoiceField(
        choices=Exercise._meta.get_field("tracking_type").choices,
    )
    instructions = serializers.CharField(required=False, allow_blank=True)

    def validate_primary_muscle_group_id(self, value):
        try:
            return MuscleGroup.objects.get(id=value, is_active=True)
        except MuscleGroup.DoesNotExist as exc:
            raise serializers.ValidationError("Мышечная группа не найдена") from exc

    def validate_equipment_id(self, value):
        if value is None:
            return None

        try:
            return Equipment.objects.get(id=value, is_active=True)
        except Equipment.DoesNotExist as exc:
            raise serializers.ValidationError("Оборудование не найдено") from exc

    def create(self, validated_data):
        primary_muscle_group = validated_data.pop("primary_muscle_group_id")
        equipment = validated_data.pop("equipment_id", None)

        return Exercise.objects.create(
            owner=self.context["request"].user,
            primary_muscle_group=primary_muscle_group,
            equipment=equipment,
            is_system=False,
            **validated_data,
        )


class UpdateExerciseSerializer(CreateExerciseSerializer):
    def update(self, instance, validated_data):
        primary_muscle_group = validated_data.pop("primary_muscle_group_id", None)
        equipment = validated_data.pop("equipment_id", None)

        if primary_muscle_group is not None:
            instance.primary_muscle_group = primary_muscle_group

        if "equipment_id" in self.initial_data:
            instance.equipment = equipment

        for field, value in validated_data.items():
            setattr(instance, field, value)

        instance.save()

        return instance
