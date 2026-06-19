import pytest
from django.core.management import call_command

from nutrition.models import Food, FoodSource


@pytest.mark.django_db
def test_seed_food_catalog_creates_system_verified_foods():
    call_command("seed_food_catalog")

    chicken = Food.objects.get(name="Chicken breast, cooked")

    assert chicken.owner is None
    assert chicken.source == FoodSource.SYSTEM
    assert chicken.is_verified is True
    assert chicken.is_active is True
    assert chicken.calories_per_100g == 165
    assert chicken.protein_per_100g == 31


@pytest.mark.django_db
def test_seed_food_catalog_is_idempotent():
    call_command("seed_food_catalog")
    first_count = Food.objects.count()

    call_command("seed_food_catalog")
    second_count = Food.objects.count()

    assert second_count == first_count
