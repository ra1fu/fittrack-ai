from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from django.contrib.auth import authenticate
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User
from accounts.services import RegisterUserCommand, register_user


class EmptyMetaSerializer(serializers.Serializer):
    pass


class AuthUserResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    email = serializers.EmailField()
    email_verified = serializers.BooleanField()


class RegisterDataResponseSerializer(AuthUserResponseSerializer):
    pass


class RegisterResponseSerializer(serializers.Serializer):
    data = RegisterDataResponseSerializer()
    meta = EmptyMetaSerializer()


class LoginDataResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = AuthUserResponseSerializer()


class LoginResponseSerializer(serializers.Serializer):
    data = LoginDataResponseSerializer()
    meta = EmptyMetaSerializer()


class RefreshDataResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField(required=False)


class RefreshResponseSerializer(serializers.Serializer):
    data = RefreshDataResponseSerializer()
    meta = EmptyMetaSerializer()


class LogoutDataResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()


class LogoutResponseSerializer(serializers.Serializer):
    data = LogoutDataResponseSerializer()
    meta = EmptyMetaSerializer()


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    accepted_terms = serializers.BooleanField(write_only=True)
    accepted_privacy = serializers.BooleanField(write_only=True)

    def validate_email(self, value: str) -> str:
        normalized_email = value.strip().lower()

        if User.objects.filter(email=normalized_email).exists():
            raise serializers.ValidationError("Пользователь с таким email уже существует")

        return normalized_email

    def validate_password(self, value: str) -> str:
        validate_password(value)
        return value

    def validate_accepted_terms(self, value: bool) -> bool:
        if value is not True:
            raise serializers.ValidationError("Необходимо принять условия использования")

        return value

    def validate_accepted_privacy(self, value: bool) -> bool:
        if value is not True:
            raise serializers.ValidationError("Необходимо принять политику конфиденциальности")

        return value

    def create(self, validated_data):
        command = RegisterUserCommand(
            email=validated_data["email"],
            password=validated_data["password"],
        )
        return register_user(command)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs["email"].strip().lower()
        password = attrs["password"]

        user = authenticate(
            request=self.context.get("request"),
            email=email,
            password=password,
        )

        if user is None:
            raise AuthenticationFailed("Неверный email или пароль")

        if not user.is_active:
            raise AuthenticationFailed("Неверный email или пароль")

        refresh = RefreshToken.for_user(user)

        return {
            "user": user,
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }


class RefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField(write_only=True)

    def validate(self, attrs):
        serializer = TokenRefreshSerializer(data=attrs)

        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as exc:
            raise InvalidToken("Токен недействителен или истёк") from exc

        return {
            "access": serializer.validated_data["access"],
            "refresh": serializer.validated_data.get("refresh"),
        }

class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(write_only=True)
    
    def validate_refresh(self, value: str) -> str:
        try:
            token = RefreshToken(value)
            token.blacklist()
        except TokenError as exc:
            raise serializers.ValidationError("Refresh token is invalid or already revoked") from exc
        
        return value
