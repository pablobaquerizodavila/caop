.PHONY: up down logs build migrate revision test lint fmt backend-shell psql

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f --tail=100

build:
	docker compose build

migrate:
	docker compose run --rm backend alembic upgrade head

revision:
	docker compose run --rm backend alembic revision --autogenerate -m "$(m)"

test:
	docker compose run --rm backend pytest -q

lint:
	docker compose run --rm backend ruff check app

fmt:
	docker compose run --rm backend ruff format app

backend-shell:
	docker compose exec backend bash

psql:
	docker compose exec postgres psql -U $${POSTGRES_USER:-caop} -d $${POSTGRES_DB:-caop}
