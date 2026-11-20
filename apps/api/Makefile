UV ?= uv
RUN := $(UV) run
LOCAL_ENV := $(if $(wildcard .env),--env-file .env)

.PHONY: sync lint format type test test-integration contracts check migrate revision run openapi

sync:
	$(UV) sync --locked

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

test-integration:
	$(RUN) pytest -q -k transactions

contracts:
	$(RUN) python scripts/contracts/route_coverage.py
	$(RUN) python scripts/contracts/task_coverage.py
	$(RUN) python scripts/contracts/queue_check.py

check: lint type contracts test

migrate:
	$(RUN) alembic upgrade head

revision:
	$(RUN) alembic revision -m "$(m)"

run:
	$(RUN) $(LOCAL_ENV) uvicorn api.main:app --host 127.0.0.1 --port 8008

openapi:
	$(RUN) python scripts/contracts/openapi.py
