# Deployment

The production manifest defines one application image for the FastAPI service,
three Celery workers, beat and the authenticated public MCP service. PostgreSQL,
Redis broker/cache and MinIO keep their existing persistent storage locations.

Build the image for the deployment host from `apps/api/Dockerfile` using
`apps/api` as the context. Use an immutable release tag. Store the production
environment outside the source checkout and restrict access to the deployment
user. See `apps/api/.env.example` for application settings. Set `JWT_SECRET` to
the existing signing key so active sessions survive the rollout. Set
`REDIS_CACHE_URL` to the shared cache for per-client authentication limits
and `FORWARDED_ALLOW_IPS` to the reverse proxy address seen by the API
container. Set `ENABLE_API_DOCS=false` to disable the public schema and docs.

```sh
export APP_IMAGE=noshiro-db/api APP_IMAGE_TAG=release-tag
export ENV_FILE=/path/to/production.env
docker compose --env-file "$ENV_FILE" -f deploy/compose.prod.yml config --quiet
docker compose --env-file "$ENV_FILE" -f deploy/compose.prod.yml up -d --wait postgres redis-broker redis-cache minio
docker compose --env-file "$ENV_FILE" -f deploy/compose.prod.yml run --rm --no-deps api alembic upgrade head
docker compose --env-file "$ENV_FILE" -f deploy/compose.prod.yml up -d --wait api mcp worker-realtime worker-ai worker-sync beat
```

Before the first upgrade from the old stack, retain a verified pre-upgrade
database backup. The refresh token tables are renamed in place. The framework
retirement revision removes generated metadata and requires empty legacy group,
grant, admin log and session tables. Restoring those tables requires the backup.

Route the public API to loopback port 8010 and the exact `/mcp` path to loopback
port 8011. The API readiness endpoint is `/health/ready/`. An unauthenticated
request to `/mcp` returns 401. Verify MCP initialization and tool discovery with an
active access token. The workers listen on `realtime`, `ai` and `sync`. Beat uses
its expiring Redis heartbeat for readiness.

The frontend is deployed independently as a static site. Build it with the
production `VITE_API_BASE_URL` and configure an `index.html` fallback for client
routes. See `apps/web/docs/deployment.md`.
