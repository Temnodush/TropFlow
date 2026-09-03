# TropFlow — трекер полезных привычек
[![chatgpt-image-(307).png](https://i.postimg.cc/rmrzfzK9/chatgpt-image-(307).png)](https://postimg.cc/ftMwLz73)

Бэкенд SPA-приложения для отслеживания полезных привычек: CRUD привычек,
JWT-авторизация, напоминания в Telegram через Celery по расписанию.

Стек: Django 6, Django REST Framework, SimpleJWT, Celery + Redis,
django-celery-beat, PostgreSQL, drf-yasg (Swagger/ReDoc), pytest + coverage.

## Установка

```bash
# 1. Виртуальное окружение и зависимости
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt

# 2. Переменные окружения
copy .env.template .env         # заполнить реальными значениями

# 3. База данных (PostgreSQL)
createdb tropflow
python manage.py migrate
```

Переменные в `.env` (пример — в `.env.template`):

| Переменная             | Назначение                              |
|------------------------|-----------------------------------------|
| `SECRET_KEY_DJANGO`    | секретный ключ Django                   |
| `DEBUG`                | режим отладки (`True`/`False`)          |
| `ALLOWED_HOSTS`        | разрешённые хосты через запятую         |
| `TIME_ZONE`            | часовой пояс (IANA), в нём задаётся время привычек |
| `CORS_ALLOWED_ORIGINS` | домены фронтенда через запятую          |
| `TELEGRAM_BOT_TOKEN`   | токен Telegram-бота                    |
| `NAME`/`USER`/`PASSWORD`/`HOST`/`PORT` | настройки PostgreSQL |
| `REDIS_HOST`/`REDIS_PORT` | адрес Redis                          |

## Запуск

```bash
# API
python manage.py runserver

# Redis должен быть запущен (для Celery)

# Celery worker (на Windows — с пулом solo)
celery -A config worker -l info -P solo

# Celery beat — запускает рассылку напоминаний каждую минуту
celery -A config beat -l info
```

Пользователь привязывает Telegram-боту свой `chat_id` через
`POST /api/set-chat-id/` (или указывает при регистрации). Напоминания
приходят в минуту, когда наступает время привычки (в часовом поясе
`TIME_ZONE` из `.env`), с учётом периодичности
(раз в N дней, N от 1 до 7) и не дублируются в течение дня.

## Тесты и покрытие

```bash
pytest                                   # все тесты
coverage run -m pytest                   # замер покрытия
coverage report -m                       # отчёт (порог 80%)
```

## Документация API

- Swagger UI: http://127.0.0.1:8000/swagger/
- ReDoc: http://127.0.0.1:8000/redoc/

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

## Валидаторы (бизнес-правила)

1. Нельзя одновременно указать вознаграждение и связанную привычку.
2. Время выполнения — не больше 120 секунд.
3. Связанная привычка должна быть приятной.
4. У приятной привычки не может быть вознаграждения или связанной привычки.
5. Периодичность — от 1 до 7 дней (не реже раза в неделю).
