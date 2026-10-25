# api-v2

The replacement service: FastAPI + SQLAlchemy 2.0 (async) + Alembic, sharing the
database with the Django service until the cutover completes.

**The directory name is temporary.** The package inside is already `api`, so the
cutover is a directory swap — delete the Django `apps/api`, `git mv apps/api-v2
apps/api` — with no import changes. Nothing in the HTTP contract or the module
path says "v2".

## Rules

1. **One schema owner.** DDL is written as SQL/Alembic here. The Django app keeps
   only the model mapping it needs to keep serving, and gains no new logic.
2. **Parity before cutover.** Every endpoint is compared field by field against
   the Django service before traffic moves (`scripts/parity.py`).
3. **Bounded contexts, not technical layers.**
   `contexts/<name>/{domain,application,infrastructure,api}`. `domain` has no
   I/O; `api` never touches SQLAlchemy directly.
4. **Signals stay out of presentation.** `contexts/signal` is internal (ranking);
   import-linter rejects a dependency from `presentation` to `signal`.

## Layout

```
src/api/
  main.py              app factory; mounts context routers
  config.py            settings (pydantic-settings)
  db.py                async engine, session factory, SessionDep
  shared/problems.py   RFC 9457 error envelope
  contexts/
    identity/          redirect resolution: which entity a request means
    presentation/      read models for the public catalogue
      detail.py
      api/             one module per group of routes
    signal/            internal metrics (never rendered)
      domain.py infrastructure.py api.py
tests/                 mirror the contexts they exercise
scripts/parity.py      old vs new comparison
```

Conventions:

- a context owns its routes and its read models; nothing reaches into another
  context's SQL;
- `api.py` when a context exposes one router, an `api/` package when it exposes
  several — the split follows size, not taste;
- `domain.py` is pure, `infrastructure.py` talks to the database, `api.py` only
  translates HTTP.

## Run

```
uv sync
uv run uvicorn api.main:app --reload --port 8009
uv run pytest
```
