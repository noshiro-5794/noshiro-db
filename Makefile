# One entry point for a repository with two toolchains. Each app keeps its own
# Makefile or package scripts; these targets only delegate.

.DEFAULT_GOAL := help

.PHONY: help check api-check api-test api-lint api-migrate api-run web-check web-install web-dev web-icons openapi

help:
	@echo "check        run every gate (API + web)"
	@echo "api-check    API: lint, tests, Django checks, migration drift"
	@echo "api-test     API: pytest"
	@echo "api-lint     API: ruff check and format check"
	@echo "api-migrate  API: bootstrap and migrate the local database"
	@echo "api-run      API: serve on 127.0.0.1:8008"
	@echo "web-install  web: install dependencies from the lockfile"
	@echo "web-dev      web: Vite dev server"
	@echo "web-check    web: format, types, lint, unit, e2e, build"
	@echo "web-icons    web: regenerate platform icons and the social card"
	@echo "openapi      API: regenerate tests/snapshots/openapi.json"

check: api-check web-check

api-check:
	$(MAKE) -C apps/api check

api-test:
	$(MAKE) -C apps/api test

api-lint:
	$(MAKE) -C apps/api lint

api-migrate:
	$(MAKE) -C apps/api migrate

api-run:
	$(MAKE) -C apps/api run

openapi:
	$(MAKE) -C apps/api openapi

web-install:
	pnpm --dir apps/web install --frozen-lockfile

web-dev:
	pnpm --dir apps/web dev

web-check:
	pnpm --dir apps/web check

web-icons:
	pnpm --dir apps/web icons
