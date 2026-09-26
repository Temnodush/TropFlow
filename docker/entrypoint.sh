#!/bin/sh
# =============================================================================
#  Точка входа для сервисов web, celery и celery-beat.
#  Скрипт написан на POSIX sh: в образе python:3.14-slim нет bash.
#
#  Что делает:
#    1. ждёт готовности PostgreSQL и Redis (база может подниматься дольше);
#    2. если RUN_MIGRATIONS=True (только сервис web) — применяет миграции
#       и собирает статику;
#    3. запускает переданную команду.
# =============================================================================
set -e

log() {
    printf '[entrypoint] %s\n' "$*"
}

# --- Ожидание зависимости по TCP-порту ----------------------------------------
# Используется стандартный python, чтобы не тянуть в образ netcat.
wait_for_port() {
    host="$1"
    port="$2"
    name="$3"
    attempts="${4:-60}"

    log "ожидаю ${name} на ${host}:${port} (до ${attempts} попыток)"
    i=1
    while [ "$i" -le "$attempts" ]; do
        if python -c "
import socket, sys
sock = socket.socket()
sock.settimeout(2)
try:
    sock.connect(('${host}', ${port}))
except OSError:
    sys.exit(1)
finally:
    sock.close()
" 2>/dev/null; then
            log "${name} доступен"
            return 0
        fi
        i=$((i + 1))
        sleep 1
    done

    log "ОШИБКА: ${name} недоступен на ${host}:${port}"
    return 1
}

wait_for_port "${DB_HOST:-db}" "${DB_PORT:-5432}" "PostgreSQL" "${DB_WAIT_ATTEMPTS:-60}"
wait_for_port "${REDIS_HOST:-redis}" "${REDIS_PORT:-6379}" "Redis" "${REDIS_WAIT_ATTEMPTS:-60}"

# --- Миграции и статика -------------------------------------------------------
# Выполняет только сервис web (RUN_MIGRATIONS=True), иначе несколько
# контейнеров одновременно запускали бы миграции.
if [ "${RUN_MIGRATIONS:-False}" = "True" ]; then
    log "применяю миграции"
    python manage.py migrate --noinput

    log "собираю статику"
    python manage.py collectstatic --noinput --clear
fi

log "запускаю: $*"
exec "$@"
