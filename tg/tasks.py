"""Celery-задачи для рассылки напоминаний о привычках в Telegram."""
import logging

import requests
from celery import shared_task
from django.conf import settings
from django.utils import timezone

from tracker.models import Habit

logger = logging.getLogger(__name__)


def send_telegram_message(chat_id, habit):
    """Отправка сообщения в Telegram. Возвращает True при успехе."""
    token = settings.TELEGRAM_BOT_TOKEN
    url = f'https://api.telegram.org/bot{token}/sendMessage'
    message = (
        'Напоминание о привычке!\n'
        f'Действие: {habit.action}\n'
        f'Место: {habit.place}\n'
        f'Время: {habit.time.strftime("%H:%M")}\n'
        f'Длительность: {habit.time_to_complete} сек.'
    )
    if habit.reward:
        message += f'\nВознаграждение: {habit.reward}'
    if habit.related_habit:
        message += f'\nПосле выполнения: {habit.related_habit.action}'
    payload = {'chat_id': chat_id, 'text': message}
    try:
        response = requests.post(url, data=payload, timeout=10)
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.error('Ошибка отправки в Telegram: %s', exc)
        return False
    return True


@shared_task
def send_habit_reminders():
    """Рассылка напоминаний по привычкам, время которых наступило."""
    # Локальное время в часовом поясе settings.TIME_ZONE (из .env)
    now = timezone.localtime()
    today = now.date()

    # Привычки, у которых время совпадает с текущим (с точностью до минуты)
    habits = Habit.objects.filter(
        time__hour=now.hour,
        time__minute=now.minute,
    )
    for habit in habits:
        # Проверяем периодичность: сегодня день выполнения?
        if habit.created_at:
            days_since_created = (today - habit.created_at.date()).days
            if days_since_created % habit.periodicity != 0:
                continue

        # Проверяем, не отправляли ли уже сегодня (чтобы не дублировать)
        if habit.last_reminded == today:
            continue

        # Отправляем, если у пользователя есть chat_id
        if not habit.user.telegram_chat_id:
            continue

        if send_telegram_message(habit.user.telegram_chat_id, habit):
            habit.last_reminded = today
            habit.save(update_fields=['last_reminded'])
