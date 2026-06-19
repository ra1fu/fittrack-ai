from django.db.models import Case, IntegerField, Q, Value, When

from nutrition.models import Food


def get_visible_foods_for_user(user):
    return Food.objects.filter(
        Q(owner__isnull=True)
        | Q(owner=user),
        is_active=True,
    )


def search_visible_foods_for_user(
    *,
    user,
    search: str | None = None,
    barcode: str | None = None,
    source: str | None = None,
    is_verified: bool | None = None,
    include_inactive: bool = False,
):
    foods = Food.objects.filter(
        Q(owner__isnull=True)
        | Q(owner=user),
    )

    if not include_inactive:
        foods = foods.filter(is_active=True)

    if search:
        normalized_search = search.strip()
        foods = foods.filter(
            Q(name__icontains=normalized_search)
            | Q(brand__icontains=normalized_search)
        ).annotate(
            relevance=Case(
                When(name__iexact=normalized_search, then=Value(0)),
                When(name__istartswith=normalized_search, then=Value(1)),
                When(name__icontains=normalized_search, then=Value(2)),
                When(brand__icontains=normalized_search, then=Value(3)),
                default=Value(4),
                output_field=IntegerField(),
            )
        ).order_by("relevance", "name", "brand")
    else:
        foods = foods.order_by("name", "brand")

    if barcode:
        foods = foods.filter(barcode=barcode.strip())

    if source:
        foods = foods.filter(source=source)

    if is_verified is not None:
        foods = foods.filter(is_verified=is_verified)

    return foods