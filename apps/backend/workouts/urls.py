from django.urls import path

from workouts.views import (
    ActiveWorkoutView,
    PersonalRecordListView,
    WorkoutCancelView,
    WorkoutDetailView,
    WorkoutExerciseCreateView,
    WorkoutExerciseDetailView,
    WorkoutFinishView,
    WorkoutListCreateView,
    WorkoutSetCreateView,
    WorkoutSetDetailView,
)

urlpatterns = [
    path("personal-records", PersonalRecordListView.as_view(), name="personal-records"),
    path("workouts", WorkoutListCreateView.as_view(), name="workouts"),
    path("workouts/active", ActiveWorkoutView.as_view(), name="workout-active"),
    path("workouts/<uuid:workout_id>/finish", WorkoutFinishView.as_view(), name="workout-finish"),
    path("workouts/<uuid:workout_id>/cancel", WorkoutCancelView.as_view(), name="workout-cancel"),
    path(
        "workouts/<uuid:workout_id>/exercises",
        WorkoutExerciseCreateView.as_view(),
        name="workout-exercises",
    ),
    path("workouts/<uuid:workout_id>", WorkoutDetailView.as_view(), name="workout-detail"),
    path(
        "workout-exercises/<uuid:workout_exercise_id>",
        WorkoutExerciseDetailView.as_view(),
        name="workout-exercise-detail",
    ),
    path(
        "workout-exercises/<uuid:workout_exercise_id>/sets",
        WorkoutSetCreateView.as_view(),
        name="workout-exercise-sets",
    ),
    path(
        "workout-sets/<uuid:workout_set_id>",
        WorkoutSetDetailView.as_view(),
        name="workout-set-detail",
    ),
]
