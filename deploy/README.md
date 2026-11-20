# Deployment

`compose.dev.yml` supplies local infrastructure. `compose.prod.yml` defines
the production services and their persistent storage.

## Development infrastructure

Run `make dev-up` from the repository root to start PostgreSQL 18 and Redis.
They listen on loopback ports 5432 and 6379. The API environment example uses
the development PostgreSQL credentials and Redis database indexes. Run
`make dev-stop` to stop both services and keep the PostgreSQL volume.

[Application startup](../README.md#local-development)

## Production environment

Build one API image for HTTP, MCP, the three Celery workers, and the scheduler.
Use a release tag and store the environment file outside the checkout.

The production environment supplies `DATABASE_URL`, `CELERY_BROKER_URL`,
`REDIS_CACHE_URL`, persistent data paths, and database and object storage
credentials. Preserve the current `JWT_SECRET` across releases to retain
active sessions. Set the allowed frontend origins, secure refresh cookies,
and `FORWARDED_ALLOW_IPS` to the reverse proxy address seen by the API
container. Set `ENABLE_API_DOCS=false` to disable schema and interactive docs.

## Roll out a release

Set the image name, release tag, and absolute environment file path. Carry
forward any operator pauses on periodic jobs before replacing the scheduler
or workers.

```sh
export APP_IMAGE=noshiro-db/api APP_IMAGE_TAG=release-tag
export ENV_FILE=/path/to/production.env

docker build --tag "$APP_IMAGE:$APP_IMAGE_TAG" apps/api
docker compose --env-file "$ENV_FILE" -f deploy/compose.prod.yml config --quiet
docker compose --env-file "$ENV_FILE" -f deploy/compose.prod.yml up -d --wait postgres redis-broker redis-cache minio
docker compose --env-file "$ENV_FILE" -f deploy/compose.prod.yml run --rm -T --no-deps api alembic upgrade head
docker compose --env-file "$ENV_FILE" -f deploy/compose.prod.yml up -d --wait api mcp worker-realtime worker-ai worker-sync beat
```

Keep a verified database backup before applying production migrations. Consult
the [migration guide](../apps/api/docs/migration.md) when the release changes
the schema.

## Reverse proxy and verification

Proxy the API to loopback port 8010 and the exact `/mcp` path to loopback
port 8011. Publish the Web build independently.

Verify `/health/ready/`, an authenticated MCP request, and each worker’s queue
subscription. An unauthenticated request to `/mcp` returns 401. The scheduler
publishes a Redis heartbeat that expires if periodic work stops. Open the
public Web site and check a direct client route after deployment.

[Publish the Web build](../apps/web/docs/deployment.md)
