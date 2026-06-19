from django.core.management.base import BaseCommand

from exercises.models import Equipment, MuscleGroup


MUSCLE_GROUPS = [
    {"code": "chest", "name": "Грудь"},
    {"code": "back", "name": "Спина"},
    {"code": "shoulders", "name": "Плечи"},
    {"code": "biceps", "name": "Бицепс"},
    {"code": "triceps", "name": "Трицепс"},
    {"code": "quadriceps", "name": "Квадрицепс"},
    {"code": "hamstrings", "name": "Бицепс бедра"},
    {"code": "glutes", "name": "Ягодицы"},
    {"code": "calves", "name": "Икры"},
    {"code": "abs", "name": "Пресс"},
    {"code": "forearms", "name": "Предплечья"},
]

EQUIPMENT = [
    {"code": "barbell", "name": "Штанга"},
    {"code": "dumbbell", "name": "Гантели"},
    {"code": "machine", "name": "Тренажёр"},
    {"code": "cable", "name": "Блок"},
    {"code": "bodyweight", "name": "Собственный вес"},
    {"code": "kettlebell", "name": "Гиря"},
    {"code": "resistance_band", "name": "Резиновая лента"},
    {"code": "smith_machine", "name": "Машина Смита"},
    {"code": "other", "name": "Другое"},
]


class Command(BaseCommand):
    help = "Seed exercise catalog reference data"

    def handle(self, *args, **options):
        created_muscle_groups = 0
        created_equipment = 0

        for item in MUSCLE_GROUPS:
            _, created = MuscleGroup.objects.update_or_create(
                code=item["code"],
                defaults={
                    "name": item["name"],
                    "is_active": True,
                },
            )
            if created:
                created_muscle_groups += 1

        for item in EQUIPMENT:
            _, created = Equipment.objects.update_or_create(
                code=item["code"],
                defaults={
                    "name": item["name"],
                    "is_active": True,
                },
            )
            if created:
                created_equipment += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded catalogs: {created_muscle_groups} muscle groups, "
                f"{created_equipment} equipment items created."
            )
        )