# TropFlow — трекер полезных привычек

[![chatgpt-image-(307).png](https://i.postimg.cc/rmrzfzK9/chatgpt-image-(307).png)](https://postimg.cc/ftMwLz73)

Бэкенд SPA-приложения для отслеживания полезных привычек: CRUD привычек,
JWT-авторизация, напоминания в Telegram через Celery по расписанию.

## Стек

- **Django 6** + **Django REST Framework** — API
- **SimpleJWT** — авторизация по токенам
- **PostgreSQL 16** — база данных
- **Celery + Redis** + **django-celery-beat** — фоновые задачи по расписанию
- **Gunicorn** — WSGI-сервер приложения
- **Nginx** — отдача статики и проксирование запросов
- **drf-yasg** — документация Swagger/ReDoc
- **Docker + Docker Compose** — запуск всего проекта одной командой
- **GitHub Actions** — CI/CD и автоматический деплой
- **pytest + coverage**, **flake8** — тесты и линтер

## Требования

- Docker и Docker Compose v2 (`docker compose version`) — для запуска проекта
- Python 3.14 — только если запускать без Docker
- PostgreSQL 16 и Redis — только если запускать без Docker

## Запуск проекта

Всё поднимается одной командой.

```bash
# 1. Создать файл с переменными окружения
copy .env.example .env          # Windows
cp .env.example .env            # Linux/macOS

# 2. Заполнить значения: SECRET_KEY_DJANGO, POSTGRES_PASSWORD,
#    при необходимости TELEGRAM_BOT_TOKEN и ALLOWED_HOSTS

# 3. Собрать и запустить все сервисы
docker compose up -d --build
```

То же самое через Makefile:

```bash
make up          # собрать и запустить
make ps          # состояние контейнеров и healthcheck
make logs        # логи (make logs S=web — только web)
make down        # остановить
```

После запуска доступно:

| Адрес                                  | Что это                      |
|----------------------------------------|------------------------------|
| http://localhost:8000/swagger/         | Swagger UI                   |
| http://localhost:8000/redoc/           | ReDoc                        |
| http://localhost:8000/admin/           | админка Django               |
| http://localhost:8000/api/habits/public/ | публичные привычки         |
| http://localhost:8000/health/          | healthcheck (отдаёт `ok`)    |

Порт задаётся переменной `WEB_PORT` в `.env` (по умолчанию `8000`).

Полезные команды после запуска:

```bash
docker compose exec web python manage.py createsuperuser  # админ
docker compose exec web python manage.py seed_demo        # демо-данные
docker compose exec web python manage.py migrate          # миграции
docker compose ps                                         # все сервисы healthy
```

Демо-данные: пользователи `demo@example.com` и `demo2@example.com`,
пароль `DemoPass123`.

Остановка:

```bash
docker compose down          # остановить, данные в томах сохраняются
docker compose down -v       # остановить и удалить тома (база, статика, медиа)
```

## Сервисы

| Сервис        | Образ                 | Назначение                                                     |
|---------------|-----------------------|----------------------------------------------------------------|
| `nginx`       | `nginx:1.27-alpine`   | единственный сервис с внешним доступом: статика, медиа, прокси |
| `web`         | сборка `Dockerfile`   | Django + Gunicorn, миграции и `collectstatic` при старте        |
| `db`          | `postgres:16-alpine`  | PostgreSQL, данные в томе `postgres_data`                      |
| `redis`       | `redis:7-alpine`      | брокер и result backend Celery                                 |
| `celery`      | тот же образ, что web | воркер: отправка напоминаний в Telegram                        |
| `celery-beat` | тот же образ, что web | планировщик: проверка привычек каждую минуту                   |

Схема:

```
браузер → nginx (порт 80) → web:8000 (Gunicorn) → Django
                                  │
                        ┌─────────┴─────────┐
                        ▼                   ▼
                  db (PostgreSQL)     redis (брокер)
                                            │
                              ┌─────────────┴─────────────┐
                              ▼                           ▼
                        celery (воркер)            celery-beat (расписание)
```

Особенности:

- образ собирается в два этапа (`staging` → `runtime`): компилятор и заголовки
  остаются в сборочном слое, в финальный образ не попадают;
- контейнеры работают не от root (пользователь `app`);
- миграции и `collectstatic` выполняет только сервис `web` — за это отвечает
  переменная `RUN_MIGRATIONS` и скрипт `docker/entrypoint.sh`;
- статика и медиа лежат в именованных томах и монтируются в Nginx только
  для чтения;
- у каждого сервиса есть `healthcheck`, а `depends_on` с условием
  `service_healthy` задаёт корректный порядок запуска.

## Переменные окружения

Все значения берутся из файла `.env` (шаблон — `.env.example`).
Файл `.env` в репозиторий не попадает.

| Переменная                        | Обязательна | Назначение                                              |
|-----------------------------------|-------------|---------------------------------------------------------|
| `SECRET_KEY_DJANGO`               | да          | секретный ключ Django                                    |
| `DEBUG`                           | нет         | `True` только локально, по умолчанию `False`             |
| `ALLOWED_HOSTS`                   | нет         | хосты через запятую; на сервере — публичный IP           |
| `CSRF_TRUSTED_ORIGINS`            | нет         | источники для CSRF, нужны для входа в админку за Nginx   |
| `CORS_ALLOWED_ORIGINS`            | нет         | домены фронтенда через запятую                           |
| `TIME_ZONE`                       | нет         | часовой пояс (IANA), в нём задаётся время привычек       |
| `TELEGRAM_BOT_TOKEN`              | нет         | токен бота; без него напоминания не отправляются         |
| `POSTGRES_DB` / `POSTGRES_USER`   | нет         | база и пользователь PostgreSQL (по умолчанию `tropflow`) |
| `POSTGRES_PASSWORD`               | да          | пароль PostgreSQL                                        |
| `REDIS_HOST` / `REDIS_PORT`       | нет         | адрес Redis; в Docker подставляется `redis:6379`         |
| `WEB_PORT`                        | нет         | порт приложения на хост-машине (по умолчанию `8000`)     |
| `GUNICORN_WORKERS`                | нет         | число воркеров Gunicorn (по умолчанию `3`)               |

Два правила, чтобы не наступить на грабли:

1. **Символ `$` в значениях недопустим** — Docker Compose считает его
   подстановкой переменной и испортит значение. Команда генерации ключа
   в `.env.example` этот символ исключает.
2. **Внутри Docker адреса базы и Redis задаются автоматически** (`db`, `redis`)
   в `docker-compose.yml`, значения из `.env` на контейнеры не влияют.

## Полезные команды

```bash
make help              # список всех команд
make up / down / stop  # запуск и остановка
make logs S=celery     # логи конкретного сервиса
make shell             # Django shell
make dbshell           # psql
make migrate           # применить миграции
make seed              # демо-данные
make test / lint       # тесты и линтер
make health            # проверить, что приложение отвечает
```

## Тесты и линтинг

```bash
pytest                       # все тесты
coverage run -m pytest       # замер покрытия
coverage report -m           # отчёт (порог 80% задан в .coveragerc)
flake8 .                     # линтер (max-line-length = 119)
```

Тесты используют PostgreSQL: без него Django не создаст тестовую базу.
Быстрый вариант — поднять только базу и Redis:

```bash
docker compose up -d db redis
python manage.py test
```

Тесты детерминированные: время подменяется через `timezone.localtime`,
а запросы к Telegram замоканы, поэтому реальные сообщения не отправляются.

## Работа с приложением

```bash
# Django shell
docker compose exec web python manage.py shell

# создать суперпользователя для админки
docker compose exec web python manage.py createsuperuser

# загрузить демонстрационные данные
docker compose exec web python manage.py seed_demo

# применить миграции
docker compose exec web python manage.py migrate

# пересобрать статику
docker compose exec web python manage.py collectstatic --noinput --clear
```

### Документация API

- Swagger UI: http://localhost:8000/swagger/
- ReDoc: http://localhost:8000/redoc/

| Метод                     | URL                    | Описание                          | Доступ        |
|---------------------------|------------------------|-----------------------------------|---------------|
| POST                      | `/api/register/`       | регистрация                       | все           |
| POST                      | `/api/token/`          | получение JWT                     | все           |
| POST                      | `/api/token/refresh/`  | обновление access-токена          | все           |
| GET                       | `/api/habits/`         | привычки пользователя (пагинация) | свои          |
| POST                      | `/api/habits/`         | создание привычки                 | авторизован   |
| GET/PUT/PATCH/DELETE      | `/api/habits/{id}/`    | просмотр/редактирование/удаление  | владелец      |
| GET                       | `/api/habits/public/`  | список публичных привычек         | все           |
| POST                      | `/api/set-chat-id/`    | привязка Telegram chat_id         | авторизован   |

Пагинация: `?limit=5&offset=0`, ответ содержит
`count`, `next`, `previous`, `limit`, `offset`, `results`.

### Напоминания в Telegram

Пользователь привязывает боту свой `chat_id` через `POST /api/set-chat-id/`
(или указывает при регистрации). Задача `tg.tasks.send_habit_reminders`
запускается Celery beat каждую минуту и отправляет напоминание, если:

- время привычки совпадает с текущей минутой (в часовом поясе `TIME_ZONE`);
- наступил день по периодичности (раз в N дней);
- сегодня напоминание ещё не отправлялось;
- у пользователя заполнен `telegram_chat_id`.

### Валидаторы (бизнес-правила)

1. Нельзя одновременно указать вознаграждение и связанную привычку.
2. Время выполнения — не больше 120 секунд.
3. Связанная привычка должна быть приятной.
4. У приятной привычки не может быть вознаграждения или связанной привычки.
5. Периодичность — от 1 до 7 дней (не реже раза в неделю).

## Запуск без Docker (опционально)

```bash
# 1. Виртуальное окружение и зависимости
python -m venv .venv
.venv\Scripts\activate           # Windows
source .venv/bin/activate        # Linux/macOS
pip install -r requirements.txt

# 2. Переменные окружения
copy .env.example .env           # заполнить реальными значениями

# 3. PostgreSQL: создать базу и применить миграции
createdb tropflow
python manage.py migrate

# 4. Redis должен быть запущен — он нужен Celery
redis-server

# 5. API
python manage.py runserver

# 6. Celery worker (в отдельном терминале; на Windows — пул solo)
celery -A config worker -l info            # Linux/macOS
celery -A config worker -l info -P solo    # Windows

# 7. Celery beat — рассылка напоминаний каждую минуту
celery -A config beat -l info
```

При запуске без Docker в `.env` должны быть заполнены `REDIS_HOST=127.0.0.1`
и параметры базы `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD`.
`config/settings.py` читает их напрямую — те же ключи, что использует
контейнер базы, поэтому отдельный набор переменных для локального запуска
не нужен.

Исключение — хост базы: в Docker он равен имени сервиса (`db`), и это
значение подставляет `docker-compose.yml`. Локально хост берётся из
`POSTGRES_HOST`, а если переменная не задана — используется `localhost`.

## Деплой на сервер (Docker)

Проект разворачивается на виртуальной машине Yandex Cloud (Ubuntu 24.04).
Docker-образы собираются прямо на сервере, реестр образов не нужен.

### Что нужно на сервере

- Docker и плагин Compose v2 (`docker compose version`);
- клон репозитория в каталоге деплоя (например `/opt/tropflow`);
- файл `.env` в каталоге деплоя — его создаёт GitHub Actions из секретов;
- открытые порты: `22` (SSH) и `80` (HTTP) в группе безопасности.

### Разовая настройка сервера

```bash
# 1. Docker (официальный установщик)
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker
docker compose version

# 2. Каталог проекта
sudo mkdir -p /opt/tropflow && sudo chown -R $USER:$USER /opt/tropflow
git clone https://github.com/Temnodush/TropFlow.git /opt/tropflow

# 3. Проверка, что проект поднимается вручную
cd /opt/tropflow
cp .env.example .env    # заполнить: SECRET_KEY_DJANGO, POSTGRES_PASSWORD,
                        # ALLOWED_HOSTS=<IP>, CSRF_TRUSTED_ORIGINS=http://<IP>
chmod 600 .env
docker compose up -d --build
```

### SSH-доступ для GitHub Actions

```bash
# 1. Ключ без пароля — им будет пользоваться раннер
ssh-keygen -t ed25519 -C "github-actions" -f ~/.ssh/tropflow_actions -N ""

# 2. Публичный ключ — на сервер
ssh-copy-id -i ~/.ssh/tropflow_actions.pub ubuntu@<IP>

# 3. Отпечаток ключа хоста понадобится позже
ssh-keyscan -H <IP>
```

### Секреты репозитория

GitHub → Settings → Secrets and variables → Actions → New repository secret:

| Секрет               | Пример / назначение                                 |
|----------------------|-----------------------------------------------------|
| `SERVER_IP`          | публичный IP сервера                                |
| `SSH_USER`           | `ubuntu`                                            |
| `SSH_KEY`            | содержимое `~/.ssh/tropflow_actions` целиком        |
| `DEPLOY_DIR`         | `/opt/tropflow`                                     |
| `SECRET_KEY_DJANGO`  | секретный ключ Django                               |
| `POSTGRES_DB`        | `tropflow`                                          |
| `POSTGRES_USER`      | `tropflow`                                          |
| `POSTGRES_PASSWORD`  | надёжный пароль                                     |
| `TELEGRAM_BOT_TOKEN` | токен бота (можно оставить пустым)                  |

Ключ и пароль можно сгенерировать так:

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

## CI/CD: GitHub Actions

Пайплайн описан в `.github/workflows/deploy.yml` и запускается на каждый push,
на pull request и вручную (`workflow_dispatch`).

| Job      | Что делает                                                                  |
|----------|-----------------------------------------------------------------------------|
| `lint`   | `flake8 .` на Python 3.14                                                    |
| `test`   | `manage.py check` и `pytest` с покрытием на реальных PostgreSQL и Redis       |
| `build`  | сборка Docker-образа (Buildx с кэшем), `docker compose build`, `compose config` |
| `deploy` | выкладка на сервер по SSH: `git pull` → `docker compose up -d --build`        |

Деплой выполняется **только при push в ветку `develop`** — pull request-ы
проверяются, но не деплоятся. После выкладки пайплайн сам проверяет, что
приложение отвечает: запрашивает `/health/` и код ответа `/swagger/`,
а при неудаче выводит логи контейнеров.

### Проверка после деплоя

```bash
curl http://<IP>/health/                                          # ok
curl -o /dev/null -w '%{http_code}\n' http://<IP>/swagger/        # 200
```

Логи на сервере:

```bash
ssh ubuntu@<IP>
cd /opt/tropflow
docker compose ps
docker compose logs -f web
```

### Обновление приложения

Достаточно сделать push в `develop` — пайплайн обновит код на сервере и
перезапустит контейнеры. Вручную то же самое:

```bash
cd /opt/tropflow
git pull
docker compose up -d --build
```

Миграции применяются автоматически при старте контейнера `web`.

> Виртуальную машину включайте только на время работы над заданием
> и останавливайте после проверки наставником: за простой списывается
> стоимость за сутки.

## Структура проекта

```
TropFlow/
├── config/                  # настройки Django, Celery, URL, WSGI/ASGI
├── tracker/                 # приложение привычек: модели, API, валидаторы
├── users/                   # пользователи: регистрация, JWT, chat_id
├── tg/                      # Telegram: отправка напоминаний, задачи Celery
├── docker/
│   └── entrypoint.sh        # ожидание базы, миграции, статика, запуск команды
├── nginx/
│   └── nginx.conf           # конфигурация Nginx для контейнера
├── .github/workflows/
│   └── deploy.yml           # CI/CD: lint → test → build → deploy
├── Dockerfile               # образ для web, celery, celery-beat
├── docker-compose.yml       # описание всех сервисов проекта
├── .env.example             # шаблон переменных окружения
├── Makefile                 # короткие команды
├── requirements.txt         # зависимости проекта
└── README.md
```

## Лицензия

Учебный проект.
