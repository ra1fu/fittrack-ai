from django.db.models import Q

from exercises.models import Exercise


def get_visible_exercises_for_user(user):
    base_query = Exercise.objects.filter(is_active=True)

    if user.is_authenticated:
        return base_query.filter(Q(is_system=True) | Q(owner=user))

    return base_query.filter(is_system=True)
