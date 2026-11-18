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

## Calendar object storage

Calendar covers use Boto3 with an S3-compatible endpoint. Configure
`S3_ENDPOINT_URL`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_BUCKET` and
`S3_PUBLIC_URL`. Existing `MINIO_*` deployment settings remain accepted as aliases.
Endpoint URLs retain their explicit HTTP/HTTPS scheme. Host-only legacy endpoints
use `MINIO_USE_HTTPS`. The public URL defaults to the endpoint URL.

Cover downloads retain `BANGUMI_IMAGE_ALLOWED_HOSTS` and
`BANGUMI_IMAGE_MAX_BYTES` and use the shared outbound proxy configuration.
Calendar quarter boundaries use `DEPLOYMENT_TIME_ZONE`, defaulting to
`Asia/Shanghai`.

## MCP entry points

Run the local internal harness with `uv run python -m api.mcp.internal`.
Run the authenticated public HTTP service with `uv run python -m api.mcp.public`.
The public endpoint is `/mcp`. Configure `MCP_HOST`, `MCP_PORT`, `MCP_RATE_LIMIT`
and `MCP_RATE_WINDOW_SECONDS`. Existing access tokens use `DJANGO_SECRET_KEY`.
The verifier checks access-token claims and active database users.

Redis rate limits use `REDIS_CACHE_URL` or the existing `CACHE_URL`, with
`CACHE_SOCKET_TIMEOUT` and `CACHE_SOCKET_CONNECT_TIMEOUT` defaulting to five
seconds. Local runs without a Redis URL use process-local fixed-window counters.
Set `NOSHIRO_INTEGRATION_REDIS_URL` to a dedicated test Redis instance to run the
concurrent limiter test alongside the PostgreSQL integration suite.

## Scheduled tasks

Start the worker with `uv run celery -A api.worker.app worker -l info` and beat
with `uv run celery -A api.worker.app beat -l info`. The application declares
the `realtime`, `sync` and `ai` queues and the existing 18 periodic jobs.
Calendar and incremental timing retain the `SYNC_CALENDAR_CRON_HOUR`,
`SYNC_CALENDAR_CRON_MINUTE`, `SYNC_INCREMENTAL_CRON_HOUR` and
`SYNC_INCREMENTAL_CRON_MINUTE` settings. Matching sweeps retain
`MATCH_CANDIDATE_SWEEP_CRON_HOURS`. `TZ` controls the scheduler timezone.
