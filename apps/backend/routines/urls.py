from django.urls import path

from routines.views import (
    RoutineDayCreateView,
    RoutineDayDetailView,
    RoutineDetailView,
    RoutineExerciseCreateView,
    RoutineExerciseDetailView,
    RoutineListCreateView,
)

urlpatterns = [
    path("routines", RoutineListCreateView.as_view(), name="routines"),
    path("routines/<uuid:routine_id>", RoutineDetailView.as_view(), name="routine-detail"),
    path(
        "routines/<uuid:routine_id>/days",
        RoutineDayCreateView.as_view(),
        name="routine-days",
    ),
    path(
        "routine-days/<uuid:routine_day_id>",
        RoutineDayDetailView.as_view(),
        name="routine-day-detail",
    ),
    path(
        "routine-days/<uuid:routine_day_id>/exercises",
        RoutineExerciseCreateView.as_view(),
        name="routine-day-exercises",
    ),
    path(
        "routine-exercises/<uuid:routine_exercise_id>",
        RoutineExerciseDetailView.as_view(),
        name="routine-exercise-detail",
    ),
]
