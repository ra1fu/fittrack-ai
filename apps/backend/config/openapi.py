from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter


def uuid_path_parameter(name: str, description: str) -> OpenApiParameter:
    return OpenApiParameter(
        name=name,
        type=OpenApiTypes.UUID,
        location=OpenApiParameter.PATH,
        required=True,
        description=description,
    )


def string_path_parameter(name: str, description: str) -> OpenApiParameter:
    return OpenApiParameter(
        name=name,
        type=OpenApiTypes.STR,
        location=OpenApiParameter.PATH,
        required=True,
        description=description,
    )


def pagination_query_parameters() -> list[OpenApiParameter]:
    return [
        OpenApiParameter(
            name="limit",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Page size from 1 to 100. Defaults to 50.",
        ),
        OpenApiParameter(
            name="offset",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Zero-based pagination offset. Defaults to 0.",
        ),
    ]
