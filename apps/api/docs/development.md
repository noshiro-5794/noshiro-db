# API development

Use Python 3.13, uv, PostgreSQL 18, and Redis. The repository's
[local infrastructure](../../../deploy/README.md#development-infrastructure)
matches the endpoints in `.env.example`.

## Local setup

From `apps/api`:

```sh
make sync
cp .env.example .env
make migrate
make run
```

Use `DATABASE_URL` for PostgreSQL, `CELERY_BROKER_URL` for job messages,
and `REDIS_CACHE_URL` for caching and shared authentication limits.
Set a local `JWT_SECRET` when exercising sign-in. Configure the S3
settings when working on avatars or mirrored artwork. Email and CAPTCHA
flows use their own provider settings.

When provider access requires a proxy, set `OUTBOUND_PROXY_URL` and
configure `OUTBOUND_NO_PROXY_HOSTS` for internal services.

## Media and schedules

Set `S3_ENDPOINT_URL`, `S3_BUCKET`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, and
`S3_PUBLIC_URL` for mirrored artwork and avatar uploads. Existing deployments
can use the supported `MINIO_*` aliases. Calendar image fetches use
`BANGUMI_IMAGE_ALLOWED_HOSTS` and `BANGUMI_IMAGE_MAX_BYTES`.

`TZ` sets the Celery scheduler timezone. `DEPLOYMENT_TIME_ZONE` sets the
calendar’s local date and season boundaries. See `api.config.Settings` for
calendar, incremental import, and matching sweep timing.

## Service entry points

| Service | Local entry point |
| --- | --- |
| HTTP | `make run` |
| Worker | `uv run --env-file .env celery -A api.worker.app worker -l info -Q realtime,ai,sync` |
| Scheduler | `uv run --env-file .env celery -A api.worker.app beat -l info` |
| Internal MCP | `uv run --env-file .env python -m api.mcp.internal` |
| Public MCP | `uv run --env-file .env python -m api.mcp.public` |

## Verification

`make check` runs Ruff, mypy, the HTTP operation and broker inventories, and
pytest. Set `NOSHIRO_INTEGRATION_DATABASE_URL` to a disposable PostgreSQL
database whose name ends in `_test` and whose schema is migrated to `head`. Set
`NOSHIRO_INTEGRATION_REDIS_URL` to a dedicated Redis database for the
concurrent limiter tests.

`make test-integration` selects the database transaction suites. The schema CI
job creates a fresh database, exercises the supported migration round trip,
and runs those suites against the current revision.

`make openapi` writes `tests/snapshots/openapi.json`. Update the Web contracts
and decoders in the same change when an HTTP payload changes.
The exporter, operation inventories, and broker checks live in `scripts/contracts/`.
