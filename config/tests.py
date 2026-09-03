"""Тесты конфигурации проекта и документации Swagger/ReDoc."""
from rest_framework import status
from rest_framework.test import APITestCase


def test_wsgi_application():
    from config.wsgi import application
    assert application is not None


def test_asgi_application():
    from config.asgi import application
    assert application is not None


class SwaggerTests(APITestCase):
    """Тесты документации API."""

    def test_swagger_ui(self):
        response = self.client.get('/swagger/')
        assert response.status_code == status.HTTP_200_OK

    def test_redoc_ui(self):
        response = self.client.get('/redoc/')
        assert response.status_code == status.HTTP_200_OK

    def test_openapi_schema_contains_endpoints(self):
        response = self.client.get('/swagger/?format=openapi')
        assert response.status_code == status.HTTP_200_OK
        paths = response.json()['paths']
        for path in (
            '/habits/',
            '/habits/public/',
            '/habits/{id}/',
            '/register/',
            '/set-chat-id/',
            '/token/',
            '/token/refresh/',
        ):
            assert path in paths, f'Путь {path} отсутствует в схеме'
