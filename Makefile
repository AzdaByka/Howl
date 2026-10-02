API_DIR=services/api

.PHONY: api-install api-test api-lint db-migrate db-upgrade openapi-export compose-up compose-down

api-install:
	uv sync --dev --directory $(API_DIR)

api-test:
	uv run --directory $(API_DIR) pytest

api-lint:
	uv run --directory $(API_DIR) ruff check app migrations tests

db-migrate:
	uv run --directory $(API_DIR) alembic revision --autogenerate -m "change"

db-upgrade:
	uv run --directory $(API_DIR) alembic upgrade head

openapi-export:
	uv run --directory $(API_DIR) python scripts/export_openapi.py

compose-up:
	docker compose up -d

compose-down:
	docker compose down
