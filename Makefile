# =============================================================================
#  TropFlow — короткие команды для повседневной работы с проектом.
#
#      make up       собрать и запустить всё одной командой
#      make test     прогнать тесты с покрытием
#      make logs     посмотреть логи
#
#  Все команды — обёртки над docker compose, отдельной логики здесь нет.
# =============================================================================

COMPOSE := docker compose

.DEFAULT_GOAL := help

.PHONY: help up build down stop restart logs ps shell dbshell migrate \
        makemigrations createsuperuser seed test lint coverage health clean

help: ## Список всех команд
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

up: ## Собрать и запустить все сервисы
	$(COMPOSE) up -d --build
	@echo "Приложение: http://localhost:8000/swagger/"

build: ## Только собрать образы
	$(COMPOSE) build

down: ## Остановить и удалить контейнеры (данные в томах сохраняются)
	$(COMPOSE) down

stop: ## Остановить контейнеры, не удаляя их
	$(COMPOSE) stop

restart: ## Перезапустить все сервисы
	$(COMPOSE) restart

logs: ## Логи всех сервисов (make logs S=web — только одного)
	$(COMPOSE) logs -f $(S)

ps: ## Состояние контейнеров и healthcheck
	$(COMPOSE) ps

shell: ## Django shell внутри контейнера web
	$(COMPOSE) exec web python manage.py shell

dbshell: ## psql внутри контейнера db
	$(COMPOSE) exec db sh -c 'psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"'

migrate: ## Применить миграции
	$(COMPOSE) exec web python manage.py migrate

makemigrations: ## Создать новые миграции
	$(COMPOSE) exec web python manage.py makemigrations

createsuperuser: ## Создать администратора для админки
	$(COMPOSE) exec web python manage.py createsuperuser

seed: ## Заполнить базу демонстрационными данными
	$(COMPOSE) exec web python manage.py seed_demo

test: ## Тесты с покрытием
	coverage run -m pytest -q && coverage report -m

lint: ## Проверка стиля кода
	flake8 .

coverage: ## HTML-отчёт о покрытии
	coverage html && @echo "Отчёт: htmlcov/index.html"

health: ## Проверить, что приложение отвечает через Nginx
	@curl -fsS http://localhost:8000/health/ && echo " — OK"

clean: ## Удалить контейнеры вместе с томами и образами проекта
	$(COMPOSE) down -v --rmi local --remove-orphans
