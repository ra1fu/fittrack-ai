from django.core.management.base import BaseCommand

from nutrition.models import Food, FoodSource


SYSTEM_FOODS = [
    {
        "name": "Chicken breast, cooked",
        "brand": "",
        "serving_size": "100.00",
        "serving_unit": "g",
        "calories_per_100g": "165.00",
        "protein_per_100g": "31.00",
        "fat_per_100g": "3.60",
        "carbs_per_100g": "0.00",
        "fiber_per_100g": "0.00",
    },
    {
        "name": "White rice, cooked",
        "brand": "",
        "serving_size": "150.00",
        "serving_unit": "g",
        "calories_per_100g": "130.00",
        "protein_per_100g": "2.70",
        "fat_per_100g": "0.30",
        "carbs_per_100g": "28.00",
        "fiber_per_100g": "0.40",
    },
    {
        "name": "Oatmeal, cooked",
        "brand": "",
        "serving_size": "200.00",
        "serving_unit": "g",
        "calories_per_100g": "71.00",
        "protein_per_100g": "2.50",
        "fat_per_100g": "1.50",
        "carbs_per_100g": "12.00",
        "fiber_per_100g": "1.70",
    },
    {
        "name": "Egg, whole",
        "brand": "",
        "serving_size": "50.00",
        "serving_unit": "g",
        "calories_per_100g": "143.00",
        "protein_per_100g": "12.60",
        "fat_per_100g": "9.50",
        "carbs_per_100g": "0.70",
        "fiber_per_100g": "0.00",
    },
    {
        "name": "Greek yogurt, plain",
        "brand": "",
        "serving_size": "170.00",
        "serving_unit": "g",
        "calories_per_100g": "59.00",
        "protein_per_100g": "10.00",
        "fat_per_100g": "0.40",
        "carbs_per_100g": "3.60",
        "fiber_per_100g": "0.00",
    },
    {
        "name": "Banana",
        "brand": "",
        "serving_size": "118.00",
        "serving_unit": "g",
        "calories_per_100g": "89.00",
        "protein_per_100g": "1.10",
        "fat_per_100g": "0.30",
        "carbs_per_100g": "23.00",
        "fiber_per_100g": "2.60",
    },
    {
        "name": "Apple",
        "brand": "",
        "serving_size": "182.00",
        "serving_unit": "g",
        "calories_per_100g": "52.00",
        "protein_per_100g": "0.30",
        "fat_per_100g": "0.20",
        "carbs_per_100g": "14.00",
        "fiber_per_100g": "2.40",
    },
    {
        "name": "Broccoli, cooked",
        "brand": "",
        "serving_size": "100.00",
        "serving_unit": "g",
        "calories_per_100g": "35.00",
        "protein_per_100g": "2.40",
        "fat_per_100g": "0.40",
        "carbs_per_100g": "7.20",
        "fiber_per_100g": "3.30",
    },
    {
        "name": "Salmon, cooked",
        "brand": "",
        "serving_size": "100.00",
        "serving_unit": "g",
        "calories_per_100g": "206.00",
        "protein_per_100g": "22.00",
        "fat_per_100g": "12.00",
        "carbs_per_100g": "0.00",
        "fiber_per_100g": "0.00",
    },
    {
        "name": "Cottage cheese",
        "brand": "",
        "serving_size": "150.00",
        "serving_unit": "g",
        "calories_per_100g": "98.00",
        "protein_per_100g": "11.10",
        "fat_per_100g": "4.30",
        "carbs_per_100g": "3.40",
        "fiber_per_100g": "0.00",
    },
]


class Command(BaseCommand):
    help = "Seed system food catalog"

    def handle(self, *args, **options):
        created_foods = 0
        updated_foods = 0

        for item in SYSTEM_FOODS:
            _, created = Food.objects.update_or_create(
                owner=None,
                source=FoodSource.SYSTEM,
                name=item["name"],
                defaults={
                    **item,
                    "data_quality": "medium",
                    "is_verified": True,
                    "is_active": True,
                },
            )

            if created:
                created_foods += 1
            else:
                updated_foods += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded food catalog: {created_foods} created, "
                f"{updated_foods} updated."
            )
        )
