from rest_framework import serializers


class EmptyMetaSerializer(serializers.Serializer):
    pass


class NutritionTotalsSerializer(serializers.Serializer):
    calories = serializers.CharField()
    protein = serializers.CharField()
    fat = serializers.CharField()
    carbs = serializers.CharField()


class NutritionTargetsSerializer(serializers.Serializer):
    active_goal_id = serializers.UUIDField(allow_null=True)
    goal_type = serializers.CharField(allow_null=True)
    calories = serializers.CharField(allow_null=True)
    protein = serializers.CharField(allow_null=True)
    fat = serializers.CharField(allow_null=True)
    carbs = serializers.CharField(allow_null=True)


class NutritionProgressItemSerializer(serializers.Serializer):
    consumed = serializers.CharField()
    target = serializers.CharField(allow_null=True)
    remaining = serializers.CharField(allow_null=True)
    percent = serializers.CharField(allow_null=True)


class NutritionProgressSerializer(serializers.Serializer):
    calories = NutritionProgressItemSerializer()
    protein = NutritionProgressItemSerializer()
    fat = NutritionProgressItemSerializer()
    carbs = NutritionProgressItemSerializer()


class DashboardNutritionSummarySerializer(serializers.Serializer):
    totals = NutritionTotalsSerializer()
    targets = NutritionTargetsSerializer()
    progress = NutritionProgressSerializer()
    meal_count = serializers.IntegerField()


class DashboardWorkoutSummarySerializer(serializers.Serializer):
    week_start = serializers.DateField()
    week_end = serializers.DateField()
    completed_workouts = serializers.IntegerField()
    total_volume = serializers.CharField()
    completed_working_sets = serializers.IntegerField()
    duration_seconds = serializers.IntegerField()


class DashboardSummaryDataSerializer(serializers.Serializer):
    date = serializers.DateField()
    nutrition = DashboardNutritionSummarySerializer()
    workouts = DashboardWorkoutSummarySerializer()


class DashboardSummaryResponseSerializer(serializers.Serializer):
    data = DashboardSummaryDataSerializer()
    meta = EmptyMetaSerializer()


class DashboardTrendNutritionSerializer(NutritionTotalsSerializer):
    meal_count = serializers.IntegerField()


class DashboardTrendWorkoutSerializer(serializers.Serializer):
    completed_workouts = serializers.IntegerField()
    total_volume = serializers.CharField()
    completed_working_sets = serializers.IntegerField()
    duration_seconds = serializers.IntegerField()


class DashboardTrendPointSerializer(serializers.Serializer):
    date = serializers.DateField()
    nutrition = DashboardTrendNutritionSerializer()
    workouts = DashboardTrendWorkoutSerializer()


class DashboardTrendsDataSerializer(serializers.Serializer):
    date_from = serializers.DateField()
    date_to = serializers.DateField()
    points = DashboardTrendPointSerializer(many=True)


class DashboardTrendsResponseSerializer(serializers.Serializer):
    data = DashboardTrendsDataSerializer()
    meta = EmptyMetaSerializer()
