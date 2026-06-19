from rest_framework import serializers


class LimitOffsetQuerySerializer(serializers.Serializer):
    limit = serializers.IntegerField(
        required=False,
        default=50,
        min_value=1,
        max_value=100,
    )
    offset = serializers.IntegerField(
        required=False,
        default=0,
        min_value=0,
    )


def paginate_queryset(queryset, query_params):
    serializer = LimitOffsetQuerySerializer(data=query_params)
    serializer.is_valid(raise_exception=True)

    limit = serializer.validated_data["limit"]
    offset = serializer.validated_data["offset"]
    total_count = queryset.count()
    page = queryset[offset:offset + limit]

    return page, {
        "count": len(page),
        "total_count": total_count,
        "limit": limit,
        "offset": offset,
    }
