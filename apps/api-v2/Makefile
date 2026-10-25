UV ?= uv
RUN := $(UV) run

.PHONY: sync lint format type test check

sync:
	$(UV) sync

lint:
	$(RUN) ruff check api tests
	$(RUN) ruff format --check api tests

format:
	$(RUN) ruff check --fix api tests
	$(RUN) ruff format api tests

type:
	$(RUN) mypy

test:
	$(RUN) pytest -q

check: lint type test
