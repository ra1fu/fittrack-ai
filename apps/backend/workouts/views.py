from routines.models import RoutineDay
from django.db.models import Prefetch
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone

from config.openapi import pagination_query_parameters, uuid_path_parameter
from config.pagination import paginate_queryset
from config.openapi_examples import WORKOUT_CREATE_EXAMPLES
from workouts.models import (
    PersonalRecordType,
    Workout,
    WorkoutExercise,
    WorkoutSet,
    WorkoutStatus,
)
from workouts.records import recalculate_personal_records_for_workout
from workouts.serializers import (
    CreateWorkoutExerciseSerializer,
    CreateWorkoutSetSerializer,
    PersonalRecordListResponseSerializer,
    PersonalRecordSerializer,
    StartWorkoutSerializer,
    UpdateWorkoutSetSerializer,
    WorkoutListResponseSerializer,
    WorkoutResponseSerializer,
    WorkoutExerciseResponseSerializer,
    WorkoutSetResponseSerializer,
    WorkoutSuccessResponseSerializer,
    WorkoutExerciseSerializer,
    WorkoutSetSerializer,
    WorkoutSerializer,
)


class WorkoutListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = WorkoutSerializer

    @extend_schema(
        tags=["Workouts"],
        operation_id="workouts_list",
        parameters=[
            OpenApiParameter(
                name="status",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                enum=[value for value, _label in WorkoutStatus.choices],
            ),
            OpenApiParameter(
                name="date_from",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Filter workouts by started_at date greater than or equal.",
            ),
            OpenApiParameter(
                name="date_to",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Filter workouts by started_at date less than or equal.",
            ),
            *pagination_query_parameters(),
        ],
        responses={200: WorkoutListResponseSerializer},
    )
    def get(self, request):
        workouts = (
            request.user.workouts.filter(deleted_at__isnull=True)
            .prefetch_related(
                Prefetch(
                    "exercises__sets",
                    queryset=WorkoutSet.objects.filter(deleted_at__isnull=True),
                )
            )
            .order_by("-started_at", "-created_at")
        )

        status_filter = request.query_params.get("status")
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")

        if status_filter:
            workouts = workouts.filter(status=status_filter)

        if date_from:
            workouts = workouts.filter(started_at__date__gte=date_from)

        if date_to:
            workouts = workouts.filter(started_at__date__lte=date_to)

        workouts, meta = paginate_queryset(workouts, request.query_params)
        serializer = WorkoutSerializer(workouts, many=True)

        return Response(
            {
                "data": serializer.data,
                "meta": meta,
            }
        )

    @extend_schema(
        tags=["Workouts"],
        operation_id="workouts_create",
        request=StartWorkoutSerializer,
        responses={201: WorkoutResponseSerializer},
        examples=WORKOUT_CREATE_EXAMPLES,
    )
    def post(self, request):
        serializer = StartWorkoutSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        try:
            workout = serializer.save()
        except RoutineDay.DoesNotExist as exc:
            raise NotFound("Тренировочный день не найден") from exc

        response_serializer = WorkoutSerializer(workout)

        return Response(
            {
                "data": response_serializer.data,
                "meta": {},
            },
            status=status.HTTP_201_CREATED,
        )


class WorkoutDetailView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = WorkoutSerializer

    @extend_schema(
        tags=["Workouts"],
        operation_id="workouts_retrieve",
        parameters=[
            uuid_path_parameter("workout_id", "Workout UUID."),
        ],
        responses={200: WorkoutResponseSerializer},
    )
    def get(self, request, workout_id):
        try:
            workout = (
                request.user.workouts.filter(deleted_at__isnull=True)
                .prefetch_related(
                    Prefetch(
                        "exercises__sets",
                        queryset=WorkoutSet.objects.filter(deleted_at__isnull=True),
                    )
                )
                .get(id=workout_id)
            )
        except Workout.DoesNotExist as exc:
            raise NotFound("Тренировка не найдена") from exc

        serializer = WorkoutSerializer(workout)

        return Response(
            {
                "data": serializer.data,
                "meta": {},
            }
        )


class ActiveWorkoutView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = WorkoutSerializer

    @extend_schema(
        tags=["Workouts"],
        operation_id="workouts_active_retrieve",
        responses={200: WorkoutResponseSerializer},
    )
    def get(self, request):
        workout = (
            request.user.workouts.filter(
                status=WorkoutStatus.ACTIVE,
                deleted_at__isnull=True,
            )
            .prefetch_related(
                Prefetch(
                    "exercises__sets",
                    queryset=WorkoutSet.objects.filter(deleted_at__isnull=True),
                )
            )
            .order_by("-started_at", "-created_at")
            .first()
        )

        if workout is None:
            return Response(
                {
                    "data": None,
                    "meta": {},
                }
            )

        serializer = WorkoutSerializer(workout)

        return Response(
            {
                "data": serializer.data,
                "meta": {},
            }
        )


class WorkoutExerciseCreateView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = WorkoutExerciseSerializer

    @extend_schema(
        tags=["Workouts"],
        operation_id="workout_exercises_create",
        request=CreateWorkoutExerciseSerializer,
        parameters=[
            uuid_path_parameter("workout_id", "Active workout UUID."),
        ],
        responses={201: WorkoutExerciseResponseSerializer},
    )
    def post(self, request, workout_id):
        workout = self._get_active_user_workout(request, workout_id)
        serializer = CreateWorkoutExerciseSerializer(
            data=request.data,
            context={
                "request": request,
                "workout": workout,
            },
        )
        serializer.is_valid(raise_exception=True)
        workout_exercise = serializer.save()

        workout.server_version += 1
        workout.save(update_fields=["server_version", "updated_at"])

        response_serializer = WorkoutExerciseSerializer(workout_exercise)

        return Response(
            {
                "data": response_serializer.data,
                "meta": {},
            },
            status=status.HTTP_201_CREATED,
        )

    def _get_active_user_workout(self, request, workout_id):
        try:
            return Workout.objects.get(
                id=workout_id,
                user=request.user,
                status=WorkoutStatus.ACTIVE,
                deleted_at__isnull=True,
            )
        except Workout.DoesNotExist as exc:
            raise NotFound("Тренировка не найдена") from exc


class WorkoutExerciseDetailView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = WorkoutExerciseSerializer

    @extend_schema(
        tags=["Workouts"],
        operation_id="workout_exercises_delete",
        parameters=[
            uuid_path_parameter("workout_exercise_id", "Workout exercise UUID."),
        ],
        responses={200: WorkoutSuccessResponseSerializer},
    )
    def delete(self, request, workout_exercise_id):
        workout_exercise = self._get_active_user_workout_exercise(
            request,
            workout_exercise_id,
        )
        workout = workout_exercise.workout
        workout_exercise.delete()

        workout.server_version += 1
        workout.save(update_fields=["server_version", "updated_at"])

        return Response(
            {
                "data": {
                    "success": True,
                },
                "meta": {},
            },
            status=status.HTTP_200_OK,
        )

    def _get_active_user_workout_exercise(self, request, workout_exercise_id):
        try:
            return WorkoutExercise.objects.select_related("workout").get(
                id=workout_exercise_id,
                workout__user=request.user,
                workout__status=WorkoutStatus.ACTIVE,
                workout__deleted_at__isnull=True,
            )
        except WorkoutExercise.DoesNotExist as exc:
            raise NotFound("Упражнение тренировки не найдено") from exc


class WorkoutSetCreateView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = WorkoutSetSerializer

    @extend_schema(
        tags=["Workouts"],
        operation_id="workout_sets_create",
        request=CreateWorkoutSetSerializer,
        parameters=[
            uuid_path_parameter(
                "workout_exercise_id",
                "Workout exercise UUID.",
            ),
        ],
        responses={201: WorkoutSetResponseSerializer},
    )
    def post(self, request, workout_exercise_id):
        workout_exercise = self._get_active_user_workout_exercise(
            request,
            workout_exercise_id,
        )
        serializer = CreateWorkoutSetSerializer(
            data=request.data,
            context={"workout_exercise": workout_exercise},
        )
        serializer.is_valid(raise_exception=True)
        workout_set = serializer.save()

        workout_exercise.workout.server_version += 1
        workout_exercise.workout.save(update_fields=["server_version", "updated_at"])

        response_serializer = WorkoutSetSerializer(workout_set)

        return Response(
            {
                "data": response_serializer.data,
                "meta": {},
            },
            status=status.HTTP_201_CREATED,
        )

    def _get_active_user_workout_exercise(self, request, workout_exercise_id):
        try:
            return WorkoutExercise.objects.select_related("workout").get(
                id=workout_exercise_id,
                workout__user=request.user,
                workout__status=WorkoutStatus.ACTIVE,
                workout__deleted_at__isnull=True,
            )
        except WorkoutExercise.DoesNotExist as exc:
            raise NotFound("Упражнение тренировки не найдено") from exc


class WorkoutSetDetailView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = WorkoutSetSerializer

    @extend_schema(
        tags=["Workouts"],
        operation_id="workout_sets_partial_update",
        request=UpdateWorkoutSetSerializer,
        parameters=[
            uuid_path_parameter("workout_set_id", "Workout set UUID."),
        ],
        responses={200: WorkoutSetResponseSerializer},
    )
    def patch(self, request, workout_set_id):
        workout_set = self._get_active_user_workout_set(request, workout_set_id)
        serializer = UpdateWorkoutSetSerializer(
            workout_set,
            data=request.data,
            context={"workout_exercise": workout_set.workout_exercise},
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        workout_set = serializer.save()

        workout_set.workout_exercise.workout.server_version += 1
        workout_set.workout_exercise.workout.save(
            update_fields=["server_version", "updated_at"]
        )

        response_serializer = WorkoutSetSerializer(workout_set)

        return Response(
            {
                "data": response_serializer.data,
                "meta": {},
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        tags=["Workouts"],
        operation_id="workout_sets_delete",
        parameters=[
            uuid_path_parameter("workout_set_id", "Workout set UUID."),
        ],
        responses={200: WorkoutSuccessResponseSerializer},
    )
    def delete(self, request, workout_set_id):
        workout_set = self._get_active_user_workout_set(request, workout_set_id)
        workout = workout_set.workout_exercise.workout
        workout_set.deleted_at = timezone.now()
        workout_set.save(update_fields=["deleted_at", "updated_at"])

        workout.server_version += 1
        workout.save(update_fields=["server_version", "updated_at"])

        return Response(
            {
                "data": {
                    "success": True,
                },
                "meta": {},
            },
            status=status.HTTP_200_OK,
        )

    def _get_active_user_workout_set(self, request, workout_set_id):
        try:
            return WorkoutSet.objects.select_related(
                "workout_exercise",
                "workout_exercise__workout",
            ).get(
                id=workout_set_id,
                deleted_at__isnull=True,
                workout_exercise__workout__user=request.user,
                workout_exercise__workout__status=WorkoutStatus.ACTIVE,
                workout_exercise__workout__deleted_at__isnull=True,
            )
        except WorkoutSet.DoesNotExist as exc:
            raise NotFound("Подход не найден") from exc


class WorkoutFinishView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = WorkoutSerializer

    @extend_schema(
        tags=["Workouts"],
        operation_id="workouts_finish",
        parameters=[
            uuid_path_parameter("workout_id", "Active workout UUID."),
        ],
        responses={200: WorkoutResponseSerializer},
    )
    def post(self, request, workout_id):
        workout = self._get_active_user_workout(request, workout_id)
        finished_at = timezone.now()
        duration_seconds = max(
            0,
            int((finished_at - workout.started_at).total_seconds()),
        )

        workout.status = WorkoutStatus.COMPLETED
        workout.finished_at = finished_at
        workout.duration_seconds = duration_seconds
        workout.server_version += 1
        workout.save(
            update_fields=[
                "status",
                "finished_at",
                "duration_seconds",
                "server_version",
                "updated_at",
            ]
        )
        recalculate_personal_records_for_workout(workout)

        serializer = WorkoutSerializer(workout)

        return Response(
            {
                "data": serializer.data,
                "meta": {},
            },
            status=status.HTTP_200_OK,
        )

    def _get_active_user_workout(self, request, workout_id):
        try:
            return Workout.objects.get(
                id=workout_id,
                user=request.user,
                status=WorkoutStatus.ACTIVE,
                deleted_at__isnull=True,
            )
        except Workout.DoesNotExist as exc:
            raise NotFound("Тренировка не найдена") from exc


class PersonalRecordListView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PersonalRecordSerializer

    @extend_schema(
        tags=["Workouts"],
        operation_id="personal_records_list",
        parameters=[
            OpenApiParameter(
                name="exercise_id",
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.QUERY,
                required=False,
            ),
            OpenApiParameter(
                name="record_type",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                enum=[value for value, _label in PersonalRecordType.choices],
            ),
            *pagination_query_parameters(),
        ],
        responses={200: PersonalRecordListResponseSerializer},
    )
    def get(self, request):
        records = request.user.personal_records.filter(is_current=True).select_related(
            "exercise",
            "workout_set",
        )

        exercise_id = request.query_params.get("exercise_id")
        record_type = request.query_params.get("record_type")

        if exercise_id:
            records = records.filter(exercise_id=exercise_id)

        if record_type:
            records = records.filter(record_type=record_type)

        records = records.order_by("exercise__name", "record_type")
        records, meta = paginate_queryset(records, request.query_params)
        serializer = PersonalRecordSerializer(records, many=True)

        return Response(
            {
                "data": serializer.data,
                "meta": meta,
            }
        )


class WorkoutCancelView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = WorkoutSerializer

    @extend_schema(
        tags=["Workouts"],
        operation_id="workouts_cancel",
        parameters=[
            uuid_path_parameter("workout_id", "Active workout UUID."),
        ],
        responses={200: WorkoutResponseSerializer},
    )
    def post(self, request, workout_id):
        workout = self._get_active_user_workout(request, workout_id)
        finished_at = timezone.now()
        duration_seconds = max(
            0,
            int((finished_at - workout.started_at).total_seconds()),
        )

        workout.status = WorkoutStatus.CANCELLED
        workout.finished_at = finished_at
        workout.duration_seconds = duration_seconds
        workout.server_version += 1
        workout.save(
            update_fields=[
                "status",
                "finished_at",
                "duration_seconds",
                "server_version",
                "updated_at",
            ]
        )

        serializer = WorkoutSerializer(workout)

        return Response(
            {
                "data": serializer.data,
                "meta": {},
            },
            status=status.HTTP_200_OK,
        )

    def _get_active_user_workout(self, request, workout_id):
        try:
            return Workout.objects.get(
                id=workout_id,
                user=request.user,
                status=WorkoutStatus.ACTIVE,
                deleted_at__isnull=True,
            )
        except Workout.DoesNotExist as exc:
            raise NotFound("Тренировка не найдена") from exc
