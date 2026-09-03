"""Тесты Telegram-рассылки: отправка сообщений и периодическая задача."""
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

import requests
from django.test import TestCase
from django.utils import timezone

from tg.tasks import send_habit_reminders, send_telegram_message
from tracker.models import Habit
from users.models import User

PASSWORD = 'StrongPass123'

# Фиксированный момент времени (детерминированные тесты рассылки)
FIXED_NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=ZoneInfo('Asia/Yekaterinburg'))


class SendTelegramMessageTests(TestCase):
    """Тесты функции отправки сообщения в Telegram."""

    def setUp(self):
        self.user = User.objects.create_user(
            email='user@example.com', password=PASSWORD, telegram_chat_id='111',
        )
        self.habit = Habit.objects.create(
            user=self.user, place='Дом', time='08:00:00', action='Зарядка', time_to_complete=30,
        )

    @patch('tg.tasks.requests.post')
    def test_success(self, post_mock):
        response_mock = Mock()
        post_mock.return_value = response_mock
        result = send_telegram_message('111', self.habit)
        assert result is True
        post_mock.assert_called_once()
        url = post_mock.call_args[0][0]
        assert url.startswith('https://api.telegram.org/bot')
        payload = post_mock.call_args[1]['data']
        assert payload['chat_id'] == '111'
        assert 'Зарядка' in payload['text']
        response_mock.raise_for_status.assert_called_once()

    @patch('tg.tasks.requests.post')
    def test_message_contains_reward(self, post_mock):
        post_mock.return_value = Mock()
        self.habit.reward = 'Десерт'
        self.habit.save()
        send_telegram_message('111', self.habit)
        text = post_mock.call_args[1]['data']['text']
        assert 'Вознаграждение: Десерт' in text

    @patch('tg.tasks.requests.post')
    def test_message_contains_related_habit(self, post_mock):
        post_mock.return_value = Mock()
        pleasant = Habit.objects.create(
            user=self.user, place='Дом', time='09:00:00', action='Ванна',
            is_pleasant=True, time_to_complete=30,
        )
        self.habit.related_habit = pleasant
        self.habit.save()
        send_telegram_message('111', self.habit)
        text = post_mock.call_args[1]['data']['text']
        assert 'После выполнения: Ванна' in text

    @patch('tg.tasks.requests.post')
    def test_request_error_returns_false(self, post_mock):
        response_mock = Mock()
        response_mock.raise_for_status.side_effect = requests.RequestException('boom')
        post_mock.return_value = response_mock
        assert send_telegram_message('111', self.habit) is False


class SendHabitRemindersTests(TestCase):
    """Тесты периодической задачи рассылки напоминаний (время зафиксировано)."""

    def setUp(self):
        self.user = User.objects.create_user(
            email='user@example.com', password=PASSWORD, telegram_chat_id='111',
        )
        self.no_chat_user = User.objects.create_user(email='nochat@example.com', password=PASSWORD)

    def _habit(self, user=None, **overrides):
        defaults = {
            'place': 'Дом',
            'time': timezone.localtime().time(),
            'action': 'Зарядка',
            'time_to_complete': 30,
        }
        defaults.update(overrides)
        return Habit.objects.create(user=user or self.user, **defaults)

    @patch('django.utils.timezone.localtime', return_value=FIXED_NOW)
    @patch('tg.tasks.send_telegram_message')
    def test_sends_and_marks_reminded(self, send_mock, _now_mock):
        send_mock.return_value = True
        habit = self._habit()
        send_habit_reminders()
        send_mock.assert_called_once_with('111', habit)
        habit.refresh_from_db()
        assert habit.last_reminded == FIXED_NOW.date()

    @patch('django.utils.timezone.localtime', return_value=FIXED_NOW)
    @patch('tg.tasks.send_telegram_message')
    def test_skips_user_without_chat_id(self, send_mock, _now_mock):
        self._habit(user=self.no_chat_user)
        send_habit_reminders()
        send_mock.assert_not_called()

    @patch('django.utils.timezone.localtime', return_value=FIXED_NOW)
    @patch('tg.tasks.send_telegram_message')
    def test_skips_wrong_time(self, send_mock, _now_mock):
        self._habit(time=(FIXED_NOW + timedelta(minutes=30)).time())
        send_habit_reminders()
        send_mock.assert_not_called()

    @patch('django.utils.timezone.localtime', return_value=FIXED_NOW)
    @patch('tg.tasks.send_telegram_message')
    def test_skips_already_reminded_today(self, send_mock, _now_mock):
        habit = self._habit()
        habit.last_reminded = FIXED_NOW.date()
        habit.save(update_fields=['last_reminded'])
        send_habit_reminders()
        send_mock.assert_not_called()

    @patch('django.utils.timezone.localtime', return_value=FIXED_NOW)
    @patch('tg.tasks.send_telegram_message')
    def test_skips_by_periodicity(self, send_mock, _now_mock):
        habit = self._habit(periodicity=2)
        Habit.objects.filter(pk=habit.pk).update(created_at=FIXED_NOW - timedelta(days=3))
        send_habit_reminders()
        send_mock.assert_not_called()

    @patch('django.utils.timezone.localtime', return_value=FIXED_NOW)
    @patch('tg.tasks.send_telegram_message')
    def test_sends_on_periodicity_day(self, send_mock, _now_mock):
        send_mock.return_value = True
        habit = self._habit(periodicity=2)
        Habit.objects.filter(pk=habit.pk).update(created_at=FIXED_NOW - timedelta(days=2))
        send_habit_reminders()
        send_mock.assert_called_once_with('111', habit)

    @patch('django.utils.timezone.localtime', return_value=FIXED_NOW)
    @patch('tg.tasks.send_telegram_message')
    def test_failed_send_not_marked(self, send_mock, _now_mock):
        send_mock.return_value = False
        habit = self._habit()
        send_habit_reminders()
        habit.refresh_from_db()
        assert habit.last_reminded is None
