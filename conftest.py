"""Общая конфигурация тестов."""
import pytest


@pytest.fixture(autouse=True)
def allow_testserver_host(settings):
    """Разрешаем хост testserver, который использует Django test client."""
    settings.ALLOWED_HOSTS = [*settings.ALLOWED_HOSTS, 'testserver']
