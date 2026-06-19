from datetime import date

from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from config.openapi_examples import DASHBOARD_SUMMARY_EXAMPLES
from analytics.serializers import (
    DashboardSummaryResponseSerializer,
    DashboardTrendsResponseSerializer,
)
from analytics.services import build_dashboard_summary, build_dashboard_trends


MAX_TRENDS_DAYS = 90


class DashboardSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Analytics"],
        operation_id="dashboard_summary",
        parameters=[
            OpenApiParameter(
                name="date",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Summary date in YYYY-MM-DD format. Defaults to today.",
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=DashboardSummaryResponseSerializer,
                description="Daily dashboard summary envelope",
            ),
        },
        examples=DASHBOARD_SUMMARY_EXAMPLES,
    )
    def get(self, request):
        summary_date = _parse_summary_date(request.query_params.get("date"))
        summary = build_dashboard_summary(
            user=request.user,
            summary_date=summary_date,
        )

        return Response(
            {
                "data": summary,
                "meta": {},
            }
        )


class DashboardTrendsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Analytics"],
        operation_id="dashboard_trends",
        parameters=[
            OpenApiParameter(
                name="date_from",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                required=True,
                description="Start date in YYYY-MM-DD format.",
            ),
            OpenApiParameter(
                name="date_to",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                required=True,
                description="End date in YYYY-MM-DD format. Maximum range is 90 days.",
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=DashboardTrendsResponseSerializer,
                description="Dashboard trend points envelope",
            ),
        },
    )
    def get(self, request):
        date_from = _parse_required_date(
            request.query_params.get("date_from"),
            field_name="date_from",
        )
        date_to = _parse_required_date(
            request.query_params.get("date_to"),
            field_name="date_to",
        )

        if date_to < date_from:
            raise ValidationError(
                {
                    "date_to": "Дата окончания не может быть раньше даты начала"
                }
            )

        if (date_to - date_from).days + 1 > MAX_TRENDS_DAYS:
            raise ValidationError(
                {
                    "date_to": f"Период не может быть больше {MAX_TRENDS_DAYS} дней"
                }
            )

        trends = build_dashboard_trends(
            user=request.user,
            date_from=date_from,
            date_to=date_to,
        )

        return Response(
            {
                "data": trends,
                "meta": {},
            }
        )


def _parse_summary_date(raw_value: str | None) -> date:
    if raw_value in (None, ""):
        return timezone.localdate()

    try:
        return date.fromisoformat(raw_value)
    except ValueError as exc:
        raise ValidationError(
            {
                "date": "Укажите дату в формате YYYY-MM-DD"
            }
        ) from exc


def _parse_required_date(raw_value: str | None, *, field_name: str) -> date:
    if raw_value in (None, ""):
        raise ValidationError(
            {
                field_name: "Укажите дату в формате YYYY-MM-DD"
            }
        )

    try:
        return date.fromisoformat(raw_value)
    except ValueError as exc:
        raise ValidationError(
            {
                field_name: "Укажите дату в формате YYYY-MM-DD"
            }
        ) from exc
