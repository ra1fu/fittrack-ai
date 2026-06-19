from django.urls import path

from profiles.views import MeView, UserGoalDetailView, UserGoalListCreateView

urlpatterns = [
    path("me", MeView.as_view(), name="profile-me"),
    path("me/goals", UserGoalListCreateView.as_view(), name="profile-goals"),
    path("me/goals/<uuid:goal_id>", UserGoalDetailView.as_view(), name="profile-goal-detail"),
]