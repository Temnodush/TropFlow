"""Тесты приложения users: модель, регистрация, JWT, привязка chat_id."""
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()

PASSWORD = 'StrongPass123'


class UserModelTests(APITestCase):
    """Тесты кастомной модели пользователя."""

    def test_create_user(self):
        user = User.objects.create_user(email='user@example.com', password=PASSWORD)
        assert user.email == 'user@example.com'
        assert user.check_password(PASSWORD)
        assert user.is_staff is False
        assert user.is_superuser is False

    def test_create_user_without_email_raises(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email='', password=PASSWORD)

    def test_create_superuser(self):
        user = User.objects.create_superuser(email='admin@example.com', password=PASSWORD)
        assert user.is_staff is True
        assert user.is_superuser is True

    def test_str(self):
        user = User.objects.create_user(email='user@example.com', password=PASSWORD)
        assert str(user) == 'user@example.com'


class RegistrationTests(APITestCase):
    """Тесты эндпоинта регистрации."""

    def setUp(self):
        self.url = reverse('register')

    def _payload(self, **overrides):
        payload = {
            'email': 'user@example.com',
            'password': PASSWORD,
            'password_confirm': PASSWORD,
        }
        payload.update(overrides)
        return payload

    def test_register_success(self):
        response = self.client.post(self.url, self._payload(), format='json')
        assert response.status_code == status.HTTP_201_CREATED
        user = User.objects.get(email='user@example.com')
        assert user.check_password(PASSWORD)

    def test_register_with_chat_id(self):
        response = self.client.post(self.url, self._payload(telegram_chat_id='12345'), format='json')
        assert response.status_code == status.HTTP_201_CREATED
        user = User.objects.get(email='user@example.com')
        assert user.telegram_chat_id == '12345'

    def test_register_password_mismatch(self):
        response = self.client.post(
            self.url, self._payload(password_confirm='OtherPass123'), format='json',
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'password_confirm' in response.data

    def test_register_weak_password(self):
        response = self.client.post(
            self.url, self._payload(password='123', password_confirm='123'), format='json',
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'password' in response.data

    def test_register_duplicate_email(self):
        User.objects.create_user(email='user@example.com', password=PASSWORD)
        response = self.client.post(self.url, self._payload(), format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TokenTests(APITestCase):
    """Тесты JWT-авторизации."""

    def setUp(self):
        self.user = User.objects.create_user(email='user@example.com', password=PASSWORD)
        self.token_url = reverse('token_obtain_pair')
        self.refresh_url = reverse('token_refresh')

    def test_obtain_token(self):
        response = self.client.post(
            self.token_url, {'email': 'user@example.com', 'password': PASSWORD}, format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        assert 'refresh' in response.data

    def test_obtain_token_wrong_password(self):
        response = self.client.post(
            self.token_url, {'email': 'user@example.com', 'password': 'WrongPass123'}, format='json',
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_token(self):
        token = self.client.post(
            self.token_url, {'email': 'user@example.com', 'password': PASSWORD}, format='json',
        ).data
        response = self.client.post(self.refresh_url, {'refresh': token['refresh']}, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data

    def test_refresh_token_invalid(self):
        response = self.client.post(self.refresh_url, {'refresh': 'invalid'}, format='json')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class SetChatIdTests(APITestCase):
    """Тесты привязки Telegram chat_id."""

    def setUp(self):
        self.user = User.objects.create_user(email='user@example.com', password=PASSWORD)
        self.url = reverse('set_chat_id')

    def test_requires_auth(self):
        response = self.client.post(self.url, {'chat_id': '12345'}, format='json')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_set_chat_id(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(self.url, {'chat_id': '12345'}, format='json')
        assert response.status_code == status.HTTP_200_OK
        self.user.refresh_from_db()
        assert self.user.telegram_chat_id == '12345'

    def test_set_chat_id_missing_field(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(self.url, {}, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'chat_id' in response.data
