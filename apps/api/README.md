# API

FastAPI, SQLAlchemy 2 async, Alembic and Pydantic v2 power the API, workers and MCP services.
Use `make check` for lint, types and tests, `make migrate` for schema upgrades,
`make run` for local HTTP serving and `make openapi` for the API contract snapshot.

See `docs/architecture.md` for module ownership and conventions.

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
