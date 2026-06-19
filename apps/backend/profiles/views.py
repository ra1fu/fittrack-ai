from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import NotFound
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from config.openapi import uuid_path_parameter
from profiles.models import UserProfile
from profiles.serializers import (
    CreateUserGoalSerializer,
    MeSerializer,
    UpdateProfileSerializer,
    UpdateUserGoalSerializer,
    UserGoalSerializer,
)


class MeView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MeSerializer

    def get(self, request):
        serializer = MeSerializer(request.user)

        return Response(
            {
                "data": serializer.data,
                "meta": {},
            }
        )

    @extend_schema(
        request=UpdateProfileSerializer,
    )
    def patch(self, request):
        profile, _created = UserProfile.objects.get_or_create(user=request.user)

        serializer = UpdateProfileSerializer(
            profile,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        response_serializer = MeSerializer(request.user)

        return Response(
            {
                "data": response_serializer.data,
                "meta": {},
            }
        )


class UserGoalListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserGoalSerializer

    def get(self, request):
        goals = request.user.goals.order_by("-active_from", "-created_at")
        serializer = UserGoalSerializer(goals, many=True)

        return Response(
            {
                "data": serializer.data,
                "meta": {},
            }
        )

    @extend_schema(
        request=CreateUserGoalSerializer,
    )
    def post(self, request):
        serializer = CreateUserGoalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        goal = serializer.save(user=request.user)

        response_serializer = UserGoalSerializer(goal)

        return Response(
            {
                "data": response_serializer.data,
                "meta": {},
            },
            status=status.HTTP_201_CREATED,
        )


class UserGoalDetailView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserGoalSerializer

    @extend_schema(
        request=UpdateUserGoalSerializer,
        parameters=[
            uuid_path_parameter("goal_id", "User goal UUID."),
        ],
    )
    def patch(self, request, goal_id):
        try:
            goal = request.user.goals.get(id=goal_id)
        except request.user.goals.model.DoesNotExist as exc:
            raise NotFound("Цель не найдена") from exc

        serializer = UpdateUserGoalSerializer(
            goal,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        goal = serializer.save()

        response_serializer = UserGoalSerializer(goal)

        return Response(
            {
                "data": response_serializer.data,
                "meta": {},
            },
            status=status.HTTP_200_OK,
        )
