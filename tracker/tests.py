"""Тесты приложения tracker: модель, валидаторы, сериализаторы, права, эндпоинты."""
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIRequestFactory, APITestCase

from tracker.models import Habit
from tracker.permissions import IsOwnerOrReadOnly
from tracker.serializers import HabitSerializer
from users.models import User

PASSWORD = 'StrongPass123'


def habit_payload(**overrides):
    """Стандартные данные для создания привычки."""
    payload = {
        'place': 'Дом',
        'time': '08:00:00',
        'action': 'Сделать зарядку',
        'time_to_complete': 60,
    }
    payload.update(overrides)
    return payload


class HabitModelTests(APITestCase):
    """Тесты модели Habit и её валидаторов."""

    def setUp(self):
        self.user = User.objects.create_user(email='user@example.com', password=PASSWORD)

    def _create(self, **overrides):
        return Habit.objects.create(user=self.user, **habit_payload(**overrides))

    def test_create_valid_habit(self):
        habit = self._create()
        assert Habit.objects.count() == 1
        assert habit.periodicity == 1
        assert habit.is_pleasant is False
        assert habit.is_public is False

    def test_str(self):
        habit = self._create()
        assert str(habit) == 'user@example.com - Сделать зарядку'

    def test_reward_and_related_conflict(self):
        pleasant = self._create(is_pleasant=True, action='Принять ванну')
        with self.assertRaises(ValidationError):
            self._create(reward='Десерт', related_habit=pleasant)

    def test_time_to_complete_over_120(self):
        with self.assertRaises(ValidationError):
            self._create(time_to_complete=121)

    def test_related_habit_must_be_pleasant(self):
        ordinary = self._create()
        with self.assertRaises(ValidationError):
            self._create(related_habit=ordinary)

    def test_pleasant_with_reward(self):
        with self.assertRaises(ValidationError):
            self._create(is_pleasant=True, reward='Десерт')

    def test_pleasant_with_related(self):
        pleasant = self._create(is_pleasant=True, action='Принять ванну')
        with self.assertRaises(ValidationError):
            self._create(is_pleasant=True, related_habit=pleasant)

    def test_periodicity_zero(self):
        with self.assertRaises(ValidationError):
            self._create(periodicity=0)

    def test_periodicity_eight(self):
        with self.assertRaises(ValidationError):
            self._create(periodicity=8)


class HabitSerializerTests(APITestCase):
    """Тесты сериализатора привычки."""

    def setUp(self):
        self.user = User.objects.create_user(email='user@example.com', password=PASSWORD)
        factory = APIRequestFactory()
        self.request = factory.post('/api/habits/')
        self.request.user = self.user
        self.context = {'request': self.request}
        self.pleasant = Habit.objects.create(
            user=self.user, **habit_payload(action='Принять ванну', is_pleasant=True),
        )
        self.ordinary = Habit.objects.create(user=self.user, **habit_payload(action='Читать'))

    def _serializer(self, data, instance=None, partial=False):
        return HabitSerializer(instance=instance, data=data, context=self.context, partial=partial)

    def test_create_sets_user_from_context(self):
        serializer = self._serializer(habit_payload())
        assert serializer.is_valid(), serializer.errors
        habit = serializer.save()
        assert habit.user == self.user

    def test_validation_cases(self):
        cases = [
            {'reward': 'Десерт', 'related_habit': self.pleasant.id},
            {'time_to_complete': 121},
            {'related_habit': self.ordinary.id},
            {'is_pleasant': True, 'reward': 'Десерт'},
            {'is_pleasant': True, 'related_habit': self.pleasant.id},
            {'periodicity': 0},
            {'periodicity': 8},
        ]
        for case in cases:
            serializer = self._serializer(habit_payload(**case))
            assert not serializer.is_valid(), f'Должна быть ошибка для {case}'

    def test_partial_update_considers_existing_values(self):
        habit = Habit.objects.create(user=self.user, **habit_payload(reward='Десерт'))
        serializer = self._serializer({'related_habit': self.pleasant.id}, instance=habit, partial=True)
        assert not serializer.is_valid()
        assert 'non_field_errors' in serializer.errors

    def test_partial_update_time_limit(self):
        habit = Habit.objects.create(user=self.user, **habit_payload())
        bad = self._serializer({'time_to_complete': 200}, instance=habit, partial=True)
        assert not bad.is_valid()
        good = self._serializer({'action': 'Новое действие'}, instance=habit, partial=True)
        assert good.is_valid(), good.errors

    def test_full_update(self):
        habit = Habit.objects.create(user=self.user, **habit_payload())
        serializer = self._serializer(habit_payload(action='Обновлённое действие'), instance=habit)
        assert serializer.is_valid(), serializer.errors
        saved = serializer.save()
        assert saved.action == 'Обновлённое действие'
        assert saved.user == self.user


class PermissionTests(APITestCase):
    """Тесты объектных прав доступа."""

    def setUp(self):
        self.owner = User.objects.create_user(email='owner@example.com', password=PASSWORD)
        self.other = User.objects.create_user(email='other@example.com', password=PASSWORD)
        self.habit = Habit.objects.create(user=self.owner, **habit_payload())
        self.perm = IsOwnerOrReadOnly()
        self.factory = APIRequestFactory()

    def _request(self, method, user):
        request = self.factory.generic(method, '/')
        request.user = user
        return request

    def test_safe_methods_allowed(self):
        assert self.perm.has_object_permission(self._request('GET', self.other), None, self.habit)

    def test_safe_methods_allowed_anon(self):
        assert self.perm.has_object_permission(self._request('OPTIONS', AnonymousUser()), None, self.habit)

    def test_owner_can_write(self):
        assert self.perm.has_object_permission(self._request('PUT', self.owner), None, self.habit)

    def test_non_owner_cannot_write(self):
        assert not self.perm.has_object_permission(self._request('DELETE', self.other), None, self.habit)


class HabitViewSetTests(APITestCase):
    """Тесты эндпоинтов привычек."""

    def setUp(self):
        self.user = User.objects.create_user(email='user@example.com', password=PASSWORD)
        self.other = User.objects.create_user(email='other@example.com', password=PASSWORD)
        self.list_url = reverse('habit-list')
        self.habit = Habit.objects.create(user=self.user, **habit_payload())

    def _detail_url(self, habit):
        return reverse('habit-detail', args=[habit.id])

    def test_anon_list_returns_empty(self):
        response = self.client.get(self.list_url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 0
        assert response.data['results'] == []

    def test_list_shows_only_own(self):
        Habit.objects.create(user=self.other, **habit_payload(action='Чужая привычка'))
        self.client.force_authenticate(self.user)
        response = self.client.get(self.list_url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        assert response.data['results'][0]['action'] == 'Сделать зарядку'

    def test_pagination_format(self):
        for number in range(6):
            Habit.objects.create(user=self.user, **habit_payload(action=f'Привычка {number}'))
        self.client.force_authenticate(self.user)
        response = self.client.get(self.list_url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 7
        assert len(response.data['results']) == 5
        assert response.data['limit'] == 5
        assert response.data['offset'] == 0
        assert response.data['next'] is not None

    def test_pagination_limit_offset_params(self):
        for number in range(6):
            Habit.objects.create(user=self.user, **habit_payload(action=f'Привычка {number}'))
        self.client.force_authenticate(self.user)
        response = self.client.get(self.list_url, {'limit': 3, 'offset': 5})
        assert response.data['count'] == 7
        assert len(response.data['results']) == 2
        assert response.data['limit'] == 3
        assert response.data['offset'] == 5

    def test_create_requires_auth(self):
        response = self.client.post(self.list_url, habit_payload(), format='json')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(self.list_url, habit_payload(), format='json')
        assert response.status_code == status.HTTP_201_CREATED
        habit = Habit.objects.get(pk=response.data['id'])
        assert habit.user == self.user

    def test_create_invalid_data(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(self.list_url, habit_payload(time_to_complete=200), format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'time_to_complete' in response.data

    def test_retrieve_own(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(self._detail_url(self.habit))
        assert response.status_code == status.HTTP_200_OK
        assert response.data['action'] == 'Сделать зарядку'

    def test_retrieve_other_returns_404(self):
        other_habit = Habit.objects.create(user=self.other, **habit_payload())
        self.client.force_authenticate(self.user)
        response = self.client.get(self._detail_url(other_habit))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_own(self):
        self.client.force_authenticate(self.user)
        response = self.client.put(
            self._detail_url(self.habit), habit_payload(action='Обновлённое действие'), format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        self.habit.refresh_from_db()
        assert self.habit.action == 'Обновлённое действие'

    def test_partial_update_own(self):
        self.client.force_authenticate(self.user)
        response = self.client.patch(self._detail_url(self.habit), {'action': 'Патч'}, format='json')
        assert response.status_code == status.HTTP_200_OK
        self.habit.refresh_from_db()
        assert self.habit.action == 'Патч'

    def test_update_other_returns_404(self):
        other_habit = Habit.objects.create(user=self.other, **habit_payload())
        self.client.force_authenticate(self.user)
        response = self.client.put(
            self._detail_url(other_habit), habit_payload(action='Взлом'), format='json',
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_destroy_own(self):
        self.client.force_authenticate(self.user)
        response = self.client.delete(self._detail_url(self.habit))
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Habit.objects.filter(pk=self.habit.pk).exists()

    def test_destroy_other_returns_404(self):
        other_habit = Habit.objects.create(user=self.other, **habit_payload())
        self.client.force_authenticate(self.user)
        response = self.client.delete(self._detail_url(other_habit))
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert Habit.objects.filter(pk=other_habit.pk).exists()

    def test_public_list_for_anonymous(self):
        Habit.objects.create(user=self.other, **habit_payload(action='Публичная привычка', is_public=True))
        Habit.objects.create(user=self.user, **habit_payload(action='Приватная привычка'))
        response = self.client.get(reverse('habit-public'))
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        assert response.data['results'][0]['action'] == 'Публичная привычка'

    def test_public_list_paginated(self):
        for number in range(6):
            Habit.objects.create(user=self.other, **habit_payload(action=f'Публичная {number}', is_public=True))
        response = self.client.get(reverse('habit-public'))
        assert response.data['count'] == 6
        assert len(response.data['results']) == 5

    def test_public_only_get(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(reverse('habit-public'), habit_payload(), format='json')
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


class SeedDemoCommandTests(APITestCase):
    """Тесты команды наполнения демо-данными."""

    def test_seed_demo_creates_data_and_is_idempotent(self):
        from django.core.management import call_command

        call_command('seed_demo', verbosity=0)
        assert User.objects.filter(email='demo@example.com').exists()
        assert User.objects.filter(email='demo2@example.com').exists()
        demo = User.objects.get(email='demo@example.com')
        assert demo.check_password('DemoPass123')
        assert demo.habits.count() == 8
        assert demo.habits.filter(is_public=True).count() == 3
        assert demo.habits.filter(is_pleasant=True).count() == 1

        # повторный запуск не создаёт дубликатов
        call_command('seed_demo', verbosity=0)
        assert User.objects.count() == 2
        assert demo.habits.count() == 8
        assert Habit.objects.count() == 10
