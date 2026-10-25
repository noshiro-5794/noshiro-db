UV ?= uv
RUN := $(UV) run

.PHONY: sync lint format type test check migrate revision

sync:
	$(UV) sync

lint:
	$(RUN) ruff check src tests scripts
	$(RUN) ruff format --check src tests scripts

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
