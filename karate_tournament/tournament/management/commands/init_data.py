# Создайте файл tournament/management/commands/init_data.py
# и выполните: python manage.py init_data

from django.core.management.base import BaseCommand
from tournament.models import Tournament
from datetime import date


class Command(BaseCommand):
    help = 'Инициализация турнира'

    def handle(self, *args, **options):
        tournament, created = Tournament.objects.get_or_create(
            name="VII ЧЕМПИОНАТ И ПЕРВЕНСТВО РЕСПУБЛИКИ ТАТАРСТАН",
            defaults={
                'date': date(2026, 3, 15),
                'registration_deadline': date(2026, 2, 25),
                'is_active': True
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS('Турнир создан'))
        else:
            self.stdout.write('Турнир уже существует')