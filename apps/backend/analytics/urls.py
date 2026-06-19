from django.urls import path

from analytics.views import DashboardSummaryView, DashboardTrendsView


urlpatterns = [
    path("dashboard/summary", DashboardSummaryView.as_view(), name="dashboard-summary"),
    path("dashboard/trends", DashboardTrendsView.as_view(), name="dashboard-trends"),
]
