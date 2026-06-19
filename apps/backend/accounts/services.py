from dataclasses import dataclass

from django.db import transaction

from accounts.models import User
from profiles.models import UserProfile


@dataclass(frozen=True)
class RegisterUserCommand:
    email: str
    password: str


@transaction.atomic
def register_user(command: RegisterUserCommand) -> User:
    user = User.objects.create_user(
        email=command.email,
        password=command.password,
    )

    UserProfile.objects.create(user=user)

    return user