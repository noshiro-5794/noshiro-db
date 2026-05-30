PYTHON ?= ./venv/bin/python
CELERY ?= ./venv/bin/celery
HOST ?= 0.0.0.0
PORT ?= 8008

.PHONY: check migrations migrate run worker beat shell incremental-status

check:
	$(PYTHON) manage.py check
	$(PYTHON) manage.py makemigrations --check --dry-run

migrations:
	$(PYTHON) manage.py makemigrations

migrate:
	$(PYTHON) manage.py migrate

run:
	$(PYTHON) manage.py runserver $(HOST):$(PORT)

worker:
	$(CELERY) -A config worker -l info

beat:
	$(CELERY) -A config beat -l info

shell:
	$(PYTHON) manage.py shell

incremental-status:
	$(PYTHON) manage.py incremental_sync --status
