from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone

from config.openapi import pagination_query_parameters, uuid_path_parameter
from config.pagination import paginate_queryset
from routines.models import RoutineDay, RoutineExercise
from routines.serializers import (
    CreateRoutineSerializer,
    CreateRoutineDaySerializer,
    CreateRoutineExerciseSerializer,
    RoutineDayResponseSerializer,
    RoutineSerializer,
    RoutineDaySerializer,
    RoutineExerciseResponseSerializer,
    RoutineExerciseSerializer,
    RoutineListResponseSerializer,
    RoutineResponseSerializer,
    RoutineSuccessResponseSerializer,
    UpdateRoutineDaySerializer,
    UpdateRoutineExerciseSerializer,
    UpdateRoutineSerializer,
)


class RoutineListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = RoutineSerializer

    @extend_schema(
        tags=["Routines"],
        operation_id="routines_list",
        parameters=pagination_query_parameters(),
        responses={200: RoutineListResponseSerializer},
    )
    def get(self, request):
        routines = (
            request.user.routines.filter(deleted_at__isnull=True)
            .prefetch_related("days__exercises")
            .order_by("name")
        )
        routines, meta = paginate_queryset(routines, request.query_params)
        serializer = RoutineSerializer(routines, many=True)

        return Response(
            {
                "data": serializer.data,
                "meta": meta,
            }
        )

    @extend_schema(
        tags=["Routines"],
        operation_id="routines_create",
        request=CreateRoutineSerializer,
        responses={201: RoutineResponseSerializer},
    )
    def post(self, request):
        serializer = CreateRoutineSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        routine = serializer.save()

        response_serializer = RoutineSerializer(routine)

        return Response(
            {
                "data": response_serializer.data,
                "meta": {},
            },
            status=status.HTTP_201_CREATED,
        )


class RoutineDetailView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = RoutineSerializer

    @extend_schema(
        tags=["Routines"],
        operation_id="routines_retrieve",
        parameters=[
            uuid_path_parameter("routine_id", "Routine UUID."),
        ],
        responses={200: RoutineResponseSerializer},
    )
    def get(self, request, routine_id):
        routine = self._get_user_routine(request, routine_id)
        serializer = RoutineSerializer(routine)

        return Response(
            {
                "data": serializer.data,
                "meta": {},
            }
        )

    @extend_schema(
        tags=["Routines"],
        operation_id="routines_partial_update",
        request=UpdateRoutineSerializer,
        parameters=[
            uuid_path_parameter("routine_id", "Routine UUID."),
        ],
        responses={200: RoutineResponseSerializer},
    )
    def patch(self, request, routine_id):
        routine = self._get_user_routine(request, routine_id)
        serializer = UpdateRoutineSerializer(
            routine,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        routine = serializer.save()

        response_serializer = RoutineSerializer(routine)

        return Response(
            {
                "data": response_serializer.data,
                "meta": {},
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        tags=["Routines"],
        operation_id="routines_delete",
        parameters=[
            uuid_path_parameter("routine_id", "Routine UUID."),
        ],
        responses={200: RoutineSuccessResponseSerializer},
    )
    def delete(self, request, routine_id):
        routine = self._get_user_routine(request, routine_id)
        routine.deleted_at = timezone.now()
        routine.is_active = False
        routine.version += 1
        routine.save(update_fields=["deleted_at", "is_active", "version", "updated_at"])

        return Response(
            {
                "data": {
                    "success": True,
                },
                "meta": {},
            },
            status=status.HTTP_200_OK,
        )

    def _get_user_routine(self, request, routine_id):
        try:
            return (
                request.user.routines.filter(deleted_at__isnull=True)
                .prefetch_related("days__exercises")
                .get(id=routine_id)
            )
        except request.user.routines.model.DoesNotExist as exc:
            raise NotFound("Программа не найдена") from exc


class RoutineDayCreateView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = RoutineDaySerializer

    @extend_schema(
        tags=["Routines"],
        operation_id="routine_days_create",
        request=CreateRoutineDaySerializer,
        parameters=[
            uuid_path_parameter("routine_id", "Parent routine UUID."),
        ],
        responses={201: RoutineDayResponseSerializer},
    )
    def post(self, request, routine_id):
        routine = self._get_user_routine(request, routine_id)
        serializer = CreateRoutineDaySerializer(
            data=request.data,
            context={"routine": routine},
        )
        serializer.is_valid(raise_exception=True)
        routine_day = serializer.save()

        routine.version += 1
        routine.save(update_fields=["version", "updated_at"])

        response_serializer = RoutineDaySerializer(routine_day)

        return Response(
            {
                "data": response_serializer.data,
                "meta": {},
            },
            status=status.HTTP_201_CREATED,
        )

    def _get_user_routine(self, request, routine_id):
        try:
            return request.user.routines.filter(deleted_at__isnull=True).get(id=routine_id)
        except request.user.routines.model.DoesNotExist as exc:
            raise NotFound("Программа не найдена") from exc


class RoutineDayDetailView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = RoutineDaySerializer

    @extend_schema(
        tags=["Routines"],
        operation_id="routine_days_partial_update",
        request=UpdateRoutineDaySerializer,
        parameters=[
            uuid_path_parameter("routine_day_id", "Routine day UUID."),
        ],
        responses={200: RoutineDayResponseSerializer},
    )
    def patch(self, request, routine_day_id):
        routine_day = self._get_user_routine_day(request, routine_day_id)
        serializer = UpdateRoutineDaySerializer(
            routine_day,
            data=request.data,
            context={"routine": routine_day.routine},
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        routine_day = serializer.save()

        routine_day.routine.version += 1
        routine_day.routine.save(update_fields=["version", "updated_at"])

        response_serializer = RoutineDaySerializer(routine_day)

        return Response(
            {
                "data": response_serializer.data,
                "meta": {},
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        tags=["Routines"],
        operation_id="routine_days_delete",
        parameters=[
            uuid_path_parameter("routine_day_id", "Routine day UUID."),
        ],
        responses={200: RoutineSuccessResponseSerializer},
    )
    def delete(self, request, routine_day_id):
        routine_day = self._get_user_routine_day(request, routine_day_id)
        routine = routine_day.routine
        routine_day.delete()

        routine.version += 1
        routine.save(update_fields=["version", "updated_at"])

        return Response(
            {
                "data": {
                    "success": True,
                },
                "meta": {},
            },
            status=status.HTTP_200_OK,
        )

    def _get_user_routine_day(self, request, routine_day_id):
        try:
            return RoutineDay.objects.select_related("routine").get(
                id=routine_day_id,
                routine__user=request.user,
                routine__deleted_at__isnull=True,
            )
        except RoutineDay.DoesNotExist as exc:
            raise NotFound("Тренировочный день не найден") from exc


class RoutineExerciseCreateView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = RoutineExerciseSerializer

    @extend_schema(
        tags=["Routines"],
        operation_id="routine_exercises_create",
        request=CreateRoutineExerciseSerializer,
        parameters=[
            uuid_path_parameter("routine_day_id", "Parent routine day UUID."),
        ],
        responses={201: RoutineExerciseResponseSerializer},
    )
    def post(self, request, routine_day_id):
        routine_day = self._get_user_routine_day(request, routine_day_id)
        serializer = CreateRoutineExerciseSerializer(
            data=request.data,
            context={
                "request": request,
                "routine_day": routine_day,
            },
        )
        serializer.is_valid(raise_exception=True)
        routine_exercise = serializer.save()

        routine_day.routine.version += 1
        routine_day.routine.save(update_fields=["version", "updated_at"])

        response_serializer = RoutineExerciseSerializer(routine_exercise)

        return Response(
            {
                "data": response_serializer.data,
                "meta": {},
            },
            status=status.HTTP_201_CREATED,
        )

    def _get_user_routine_day(self, request, routine_day_id):
        try:
            return RoutineDay.objects.select_related("routine").get(
                id=routine_day_id,
                routine__user=request.user,
                routine__deleted_at__isnull=True,
            )
        except RoutineDay.DoesNotExist as exc:
            raise NotFound("Тренировочный день не найден") from exc


class RoutineExerciseDetailView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = RoutineExerciseSerializer

    @extend_schema(
        tags=["Routines"],
        operation_id="routine_exercises_partial_update",
        request=UpdateRoutineExerciseSerializer,
        parameters=[
            uuid_path_parameter("routine_exercise_id", "Routine exercise UUID."),
        ],
        responses={200: RoutineExerciseResponseSerializer},
    )
    def patch(self, request, routine_exercise_id):
        routine_exercise = self._get_user_routine_exercise(
            request,
            routine_exercise_id,
        )
        serializer = UpdateRoutineExerciseSerializer(
            routine_exercise,
            data=request.data,
            context={
                "request": request,
                "routine_day": routine_exercise.routine_day,
            },
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        routine_exercise = serializer.save()

        routine_exercise.routine_day.routine.version += 1
        routine_exercise.routine_day.routine.save(
            update_fields=["version", "updated_at"]
        )

        response_serializer = RoutineExerciseSerializer(routine_exercise)

        return Response(
            {
                "data": response_serializer.data,
                "meta": {},
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        tags=["Routines"],
        operation_id="routine_exercises_delete",
        parameters=[
            uuid_path_parameter("routine_exercise_id", "Routine exercise UUID."),
        ],
        responses={200: RoutineSuccessResponseSerializer},
    )
    def delete(self, request, routine_exercise_id):
        routine_exercise = self._get_user_routine_exercise(
            request,
            routine_exercise_id,
        )
        routine = routine_exercise.routine_day.routine
        routine_exercise.delete()

        routine.version += 1
        routine.save(update_fields=["version", "updated_at"])

        return Response(
            {
                "data": {
                    "success": True,
                },
                "meta": {},
            },
            status=status.HTTP_200_OK,
        )

    def _get_user_routine_exercise(self, request, routine_exercise_id):
        try:
            return RoutineExercise.objects.select_related(
                "routine_day",
                "routine_day__routine",
            ).get(
                id=routine_exercise_id,
                routine_day__routine__user=request.user,
                routine_day__routine__deleted_at__isnull=True,
            )
        except RoutineExercise.DoesNotExist as exc:
            raise NotFound("Упражнение в программе не найдено") from exc
