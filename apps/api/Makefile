UV ?= uv
RUN := $(UV) run

.PHONY: sync lint format type test check migrate revision run openapi

sync:
	$(UV) sync

lint:
	$(RUN) ruff check src tests scripts migrations
	$(RUN) ruff format --check src tests scripts migrations

format:
	$(RUN) ruff check --fix src tests
	$(RUN) ruff format src tests

type:
	$(RUN) mypy

test:
	$(RUN) pytest -q

check: lint type test

migrate:
	$(RUN) alembic upgrade head

revision:
	$(RUN) alembic revision -m "$(m)"

run:
	$(RUN) uvicorn api.main:app --host 127.0.0.1 --port 8008

openapi:
	$(RUN) python scripts/openapi.py
