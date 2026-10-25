UV ?= uv
RUN := $(UV) run

.PHONY: sync lint format type test check

sync:
	$(UV) sync

lint:
	$(RUN) ruff check noshiro tests
	$(RUN) ruff format --check noshiro tests

format:
	$(RUN) ruff check --fix noshiro tests
	$(RUN) ruff format noshiro tests

type:
	$(RUN) mypy

test:
	$(RUN) pytest -q

check: lint type test
