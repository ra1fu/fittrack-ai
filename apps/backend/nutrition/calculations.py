from decimal import Decimal, ROUND_HALF_UP


def calculate_nutrients_for_weight(food, weight_g: Decimal) -> dict:
    return calculate_nutrients_from_per_100g(
        calories_per_100g=food.calories_per_100g,
        protein_per_100g=food.protein_per_100g,
        fat_per_100g=food.fat_per_100g,
        carbs_per_100g=food.carbs_per_100g,
        weight_g=weight_g,
    )


def calculate_nutrients_from_per_100g(
    *,
    calories_per_100g: Decimal,
    protein_per_100g: Decimal,
    fat_per_100g: Decimal,
    carbs_per_100g: Decimal,
    weight_g: Decimal,
) -> dict:
    multiplier = weight_g / Decimal("100")

    return {
        "calories": _quantize(calories_per_100g * multiplier),
        "protein": _quantize(protein_per_100g * multiplier),
        "fat": _quantize(fat_per_100g * multiplier),
        "carbs": _quantize(carbs_per_100g * multiplier),
    }


def calculate_nutrients_for_servings(food, servings: Decimal) -> dict:
    if food.serving_size is None:
        raise ValueError("Food serving size is required for serving calculation")

    return calculate_nutrients_for_weight(food, food.serving_size * servings)


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
