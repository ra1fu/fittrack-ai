from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("api/v1/auth/", include("accounts.urls")),
    path("api/v1/", include("profiles.urls")),
    path("api/v1/", include("exercises.urls")),
    path("api/v1/", include("routines.urls")),
    path("api/v1/", include("workouts.urls")),
    path("api/v1/", include("nutrition.urls")),
    path("api/v1/", include("analytics.urls")),
    path("api/v1/health/", include("health.urls")),
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/v1/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]
