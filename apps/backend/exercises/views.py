from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import NotAuthenticated, NotFound, PermissionDenied

from config.openapi import uuid_path_parameter
from exercises.models import Equipment, Exercise, ExerciseTrackingType, MuscleGroup
from exercises.selectors import get_visible_exercises_for_user
from exercises.serializers import (
    CreateExerciseSerializer,
    EquipmentSerializer,
    ExerciseSerializer,
    MuscleGroupSerializer,
    UpdateExerciseSerializer,
)


class MuscleGroupListView(APIView):
    permission_classes = [AllowAny]
    serializer_class = MuscleGroupSerializer

    def get(self, request):
        muscle_groups = MuscleGroup.objects.filter(is_active=True).order_by("name")
        serializer = MuscleGroupSerializer(muscle_groups, many=True)

        return Response(
            {
                "data": serializer.data,
                "meta": {},
            }
        )


class EquipmentListView(APIView):
    permission_classes = [AllowAny]
    serializer_class = EquipmentSerializer

    def get(self, request):
        equipment = Equipment.objects.filter(is_active=True).order_by("name")
        serializer = EquipmentSerializer(equipment, many=True)

        return Response(
            {
                "data": serializer.data,
                "meta": {},
            }
        )

class ExerciseListView(APIView):
    permission_classes = [AllowAny]
    serializer_class = ExerciseSerializer

    @extend_schema(
        tags=["Exercises"],
        operation_id="exercises_list",
        parameters=[
            OpenApiParameter(
                name="search",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Case-insensitive exercise name search.",
            ),
            OpenApiParameter(
                name="muscle_group",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Primary muscle group code, for example chest.",
            ),
            OpenApiParameter(
                name="equipment",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Equipment code, for example barbell.",
            ),
            OpenApiParameter(
                name="tracking_type",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                enum=[value for value, _label in ExerciseTrackingType.choices],
            ),
        ],
    )
    def get(self, request):
        exercises = get_visible_exercises_for_user(request.user).select_related(
            "primary_muscle_group",
            "equipment",
            "owner",
        )

        search = request.query_params.get("search")
        muscle_group = request.query_params.get("muscle_group")
        equipment = request.query_params.get("equipment")
        tracking_type = request.query_params.get("tracking_type")

        if search:
            exercises = exercises.filter(name__icontains=search.strip())

        if muscle_group:
            exercises = exercises.filter(primary_muscle_group__code=muscle_group)

        if equipment:
            exercises = exercises.filter(equipment__code=equipment)

        if tracking_type:
            exercises = exercises.filter(tracking_type=tracking_type)

        serializer = ExerciseSerializer(exercises.order_by("name"), many=True)

        return Response(
            {
                "data": serializer.data,
                "meta": {},
            }
        )

    @extend_schema(
        tags=["Exercises"],
        operation_id="exercises_create",
        request=CreateExerciseSerializer,
    )
    def post(self, request):
        if not request.user.is_authenticated:
            raise NotAuthenticated()

        serializer = CreateExerciseSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        exercise = serializer.save()

        response_serializer = ExerciseSerializer(exercise)

        return Response(
            {
                "data": response_serializer.data,
                "meta": {},
            },
            status=status.HTTP_201_CREATED,
        )


class ExerciseDetailView(APIView):
    permission_classes = [AllowAny]
    serializer_class = ExerciseSerializer

    @extend_schema(
        tags=["Exercises"],
        operation_id="exercises_retrieve",
        parameters=[
            uuid_path_parameter("exercise_id", "Exercise UUID."),
        ],
    )
    def get(self, request, exercise_id):
        try:
            exercise = (
                get_visible_exercises_for_user(request.user)
                .select_related("primary_muscle_group", "equipment", "owner")
                .get(id=exercise_id)
            )
        except Exercise.DoesNotExist as exc:
            raise NotFound("Упражнение не найдено") from exc

        serializer = ExerciseSerializer(exercise)

        return Response(
            {
                "data": serializer.data,
                "meta": {},
            }
        )

    @extend_schema(
        tags=["Exercises"],
        operation_id="exercises_partial_update",
        request=UpdateExerciseSerializer,
        parameters=[
            uuid_path_parameter("exercise_id", "Exercise UUID."),
        ],
    )
    def patch(self, request, exercise_id):
        exercise = self._get_owned_custom_exercise_for_write(request, exercise_id)

        serializer = UpdateExerciseSerializer(
            exercise,
            data=request.data,
            context={"request": request},
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        exercise = serializer.save()

        response_serializer = ExerciseSerializer(exercise)

        return Response(
            {
                "data": response_serializer.data,
                "meta": {},
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        tags=["Exercises"],
        operation_id="exercises_delete",
        parameters=[
            uuid_path_parameter("exercise_id", "Exercise UUID."),
        ],
    )
    def delete(self, request, exercise_id):
        exercise = self._get_owned_custom_exercise_for_write(request, exercise_id)
        exercise.is_active = False
        exercise.save(update_fields=["is_active", "updated_at"])

        return Response(
            {
                "data": {
                    "success": True,
                },
                "meta": {},
            },
            status=status.HTTP_200_OK,
        )

    def _get_owned_custom_exercise_for_write(self, request, exercise_id):
        if not request.user.is_authenticated:
            raise NotAuthenticated()

        try:
            exercise = Exercise.objects.get(id=exercise_id, is_active=True)
        except Exercise.DoesNotExist as exc:
            raise NotFound("Упражнение не найдено") from exc

        if exercise.is_system:
            raise PermissionDenied("Системное упражнение нельзя изменять")

        if exercise.owner_id != request.user.id:
            raise NotFound("Упражнение не найдено")

        return exercise
