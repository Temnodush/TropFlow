# =============================================================================
#  Образ TropFlow для всех python-сервисов проекта:
#  web (Gunicorn), celery, celery-beat.
#
#  Один образ на три сервиса: отличается только команда запуска
#  (см. docker-compose.yml), поэтому код и зависимости собираются один раз.
#
#  staging — сборочный слой: компилятор и заголовки нужны, если для пакета
#  нет готового wheel. В финальный образ они не попадают.
# =============================================================================

# ------------------------------------------------------------------ staging ---
FROM python:3.14-slim AS staging

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# gcc и libpq-dev нужны для psycopg2, если сборка идёт из исходников
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Зависимости в отдельном venv: его целиком можно скопировать в финальный образ
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Зависимости копируются отдельно: слой кэшируется и не пересобирается при правках кода
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# ------------------------------------------------------------------ runtime ---
FROM python:3.14-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=config.settings \
    GUNICORN_WORKERS=3

WORKDIR /app

# libpq5 нужен psycopg2 в рантайме, curl — для healthcheck контейнера web
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

# Контейнер работает не от root
RUN useradd --system --create-home --shell /usr/sbin/nologin app

COPY --from=staging /opt/venv /opt/venv

# Конфиги инструментов нужны внутри образа: в контейнере гоняются flake8 и pytest
COPY .flake8 .coveragerc pytest.ini conftest.py ./

# Код проекта (.env, .venv, __pycache__ и прочее исключены через .dockerignore)
COPY . .

# Точка входа: ждёт базу и Redis, применяет миграции и собирает статику,
# затем запускает команду сервиса.
# Права выставляются через RUN, а не COPY --chmod: сборка работает и без BuildKit.
COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod 0755 /usr/local/bin/entrypoint.sh

# Каталоги: staticfiles отдаёт Nginx из общего тома, media — загруженные файлы,
# tmp — сюда coverage и pytest пишут свои файлы (каталог /app принадлежит root)
RUN mkdir -p /app/staticfiles /app/media /app/tmp \
    && chown -R app:app /app/staticfiles /app/media /app/tmp

USER app

EXPOSE 8000

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# Gunicorn вместо manage.py runserver: runserver не предназначен для боевой работы
CMD ["sh", "-c", "exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers \"$GUNICORN_WORKERS\" --access-logfile - --error-logfile -"]
