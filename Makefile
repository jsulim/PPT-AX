.PHONY: up down migrate test lint shell

up:
	docker compose up -d --build

down:
	docker compose down

migrate:
	docker compose run --rm api uv run alembic upgrade head

test:
	docker compose run --rm api uv run pytest
	docker compose run --rm web npm run typecheck

lint:
	docker compose run --rm api uv run ruff check .
	docker compose run --rm api uv run mypy core
	docker compose run --rm web npm run lint

shell:
	docker compose run --rm api bash
