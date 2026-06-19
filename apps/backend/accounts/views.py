from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from config.openapi_examples import (
    AUTH_LOGIN_EXAMPLES,
    AUTH_LOGOUT_EXAMPLES,
    AUTH_REFRESH_EXAMPLES,
    AUTH_REGISTER_EXAMPLES,
)
from accounts.serializers import (
    LoginSerializer,
    LoginResponseSerializer,
    LogoutSerializer,
    LogoutResponseSerializer,
    RefreshSerializer,
    RefreshResponseSerializer,
    RegisterResponseSerializer,
    RegisterSerializer,
)

class RegisterView(APIView):
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    @extend_schema(
        tags=["Auth"],
        operation_id="auth_register",
        request=RegisterSerializer,
        responses={
            201: OpenApiResponse(
                response=RegisterResponseSerializer,
                description="Registered user envelope",
            ),
        },
        examples=AUTH_REGISTER_EXAMPLES,
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.save()

        return Response(
            {
                "data": {
                    "id": str(user.id),
                    "email": user.email,
                    "email_verified": user.email_verified,
                },
                "meta": {},
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    @extend_schema(
        tags=["Auth"],
        operation_id="auth_login",
        request=LoginSerializer,
        responses={
            200: OpenApiResponse(
                response=LoginResponseSerializer,
                description="JWT token pair and current user envelope",
            ),
        },
        examples=AUTH_LOGIN_EXAMPLES,
    )
    def post(self, request):
        serializer = LoginSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]

        return Response(
            {
                "data": {
                    "access": serializer.validated_data["access"],
                    "refresh": serializer.validated_data["refresh"],
                    "user": {
                        "id": str(user.id),
                        "email": user.email,
                        "email_verified": user.email_verified,
                    },
                },
                "meta": {},
            },
            status=status.HTTP_200_OK,
        )


class RefreshView(APIView):
    permission_classes = [AllowAny]
    serializer_class = RefreshSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    @extend_schema(
        tags=["Auth"],
        operation_id="auth_refresh",
        request=RefreshSerializer,
        responses={
            200: OpenApiResponse(
                response=RefreshResponseSerializer,
                description="Rotated access token envelope",
            ),
        },
        examples=AUTH_REFRESH_EXAMPLES,
    )
    def post(self, request):
        serializer = RefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = {
            "access": serializer.validated_data["access"],
        }

        if serializer.validated_data.get("refresh"):
            data["refresh"] = serializer.validated_data["refresh"]

        return Response(
            {
                "data": data,
                "meta": {},
            },
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    permission_classes = [AllowAny]
    serializer_class = LogoutSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    @extend_schema(
        tags=["Auth"],
        operation_id="auth_logout",
        request=LogoutSerializer,
        responses={
            200: OpenApiResponse(
                response=LogoutResponseSerializer,
                description="Refresh token revocation result envelope",
            ),
        },
        examples=AUTH_LOGOUT_EXAMPLES,
    )
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        return Response(
            {
                "data": {
                    "success": True,
                },
                "meta": {},
            },
            status=status.HTTP_200_OK,
        )
