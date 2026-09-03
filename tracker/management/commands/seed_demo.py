"""Наполнение БД демонстрационными данными для ручного тестирования.

Запуск: python manage.py seed_demo
Команда идемпотентна: повторный запуск не создаёт дубликатов.
"""
from datetime import time as dt_time

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from tracker.models import Habit

User = get_user_model()

DEMO_PASSWORD = 'DemoPass123'


def parse_time(value):
    """Преобразует строку 'HH:MM:SS' в объект time."""
    return dt_time.fromisoformat(value)


class Command(BaseCommand):
    help = 'Создаёт демонстрационных пользователей и привычки для ручного тестирования.'

    def handle(self, *args, **options):
        self.stats = {'users': 0, 'habits': 0}

        demo = self._user('demo@example.com')
        second = self._user('demo2@example.com')

        # ---------- demo@example.com (8 привычек — для проверки пагинации) ----------

        # Приятная привычка (нужна как связанная для полезной)
        pleasant_bath = self._habit(
            demo, 'Принять ванну с пеной', 'Ванная комната', '20:00:00',
            30, is_pleasant=True,
        )
        # Полезная привычка со связанной приятной привычкой
        self._habit(
            demo, 'Погулять вокруг квартала после ужина', 'Двор', '19:00:00',
            120, related_habit=pleasant_bath,
        )
        # Полезная привычка с вознаграждением (публичная)
        self._habit(
            demo, 'Сделать зарядку 10 минут', 'Дом', '07:30:00', 60,
            reward='Чашка кофе', is_public=True,
        )
        self._habit(
            demo, 'Выпить стакан воды после пробуждения', 'Кухня', '08:00:00', 15,
        )
        # Привычка раз в неделю (periodicity=7)
        self._habit(
            demo, 'Позвонить родителям', 'Телефон', '18:00:00', 30,
            reward='Сладкий десерт', periodicity=7,
        )
        # Публичная привычка с вознаграждением
        self._habit(
            demo, 'Читать 10 страниц книги', 'Кровать', '22:30:00', 30,
            reward='15 минут в телефоне', is_public=True,
        )
        self._habit(
            demo, 'Помедитировать', 'Коврик', '21:00:00', 90,
            reward='Яблоко',
        )
        self._habit(
            demo, 'Проветрить комнату', 'Комната', '12:00:00', 20,
            is_public=True,
        )

        # ---------- demo2@example.com ----------

        # Публичная привычка другого пользователя (для проверки /api/habits/public/)
        self._habit(
            second, 'Пробежка в парке', 'Парк', '07:00:00', 120,
            reward='Протеиновый коктейль', is_public=True,
        )
        self._habit(
            second, 'Заправить кровать', 'Спальня', '09:00:00', 30,
        )

        self.stdout.write(self.style.SUCCESS(
            f'Готово: создано пользователей — {self.stats["users"]}, '
            f'привычек — {self.stats["habits"]}.'
        ))
        self.stdout.write('Пароль для обоих пользователей: ' + DEMO_PASSWORD)

    def _user(self, email):
        user = User.objects.filter(email=email).first()
        if user is None:
            user = User(email=email)
            user.set_password(DEMO_PASSWORD)
            user.save()
            self.stats['users'] += 1
            self.stdout.write(f'Создан пользователь: {email} / {DEMO_PASSWORD}')
        return user

    def _habit(self, user, action, place, start_time, time_to_complete,
               periodicity=1, reward=None, related_habit=None,
               is_pleasant=False, is_public=False):
        habit = Habit.objects.filter(user=user, action=action).first()
        if habit is not None:
            return habit
        habit = Habit.objects.create(
            user=user,
            action=action,
            place=place,
            time=parse_time(start_time),
            time_to_complete=time_to_complete,
            periodicity=periodicity,
            reward=reward,
            related_habit=related_habit,
            is_pleasant=is_pleasant,
            is_public=is_public,
        )
        self.stats['habits'] += 1
        self.stdout.write(f'Создана привычка: «{action}» ({user.email})')
        return habit
