from django.urls import path

from exercises.views import (
    EquipmentListView,
    ExerciseDetailView,
    ExerciseListView,
    MuscleGroupListView,
)

urlpatterns = [
    path("muscle-groups", MuscleGroupListView.as_view(), name="muscle-groups"),
    path("equipment", EquipmentListView.as_view(), name="equipment"),
    path("exercises", ExerciseListView.as_view(), name="exercises"),
    path("exercises/<uuid:exercise_id>", ExerciseDetailView.as_view(), name="exercise-detail"),
]