from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from health.serializers import HealthResponseSerializer


class HealthCheckView(APIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(
        tags=["Health"],
        operation_id="health_check",
        responses={
            200: OpenApiResponse(
                response=HealthResponseSerializer,
                description="Service health envelope",
            ),
        },
    )
    def get(self, request):
        return Response(
            {
                "data": {
                    "status": "ok",
                    "service": "fittrack-backend",
                },
                "meta": {},
            }
        )
