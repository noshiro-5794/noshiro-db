# Deployment

Production runs one Compose project (`noshiro-db`) assembled from two files:

```text
docker-compose.infra.yml  postgres, redis-broker, redis-cache, minio
docker-compose.app.yml    web, worker-realtime, worker-ai, worker-sync, beat, mcp
```

They share the `noshiro_net` Docker network. Application containers reach
infrastructure by service name instead of `host.docker.internal`.

## Configure

```bash
cp .env.production.example .env.production
```

Replace every placeholder. Validate allowed hosts, CORS and CSRF origins, secure
refresh cookies, PostgreSQL, Redis, MinIO, email, captcha, provider settings, and
timeouts. Never commit `.env.production` or put secrets in an image or Compose file.

Outbound HTTP proxying is configured only by `OUTBOUND_PROXY_URL` and
`OUTBOUND_NO_PROXY_HOSTS` in this file; the application applies them through
`shared.outbound`. Do not re-declare those keys in a Compose `environment:` block:
`${VAR:-}` interpolation reads the Compose project environment rather than the env
file, so a plain `docker compose up -d` would silently replace a configured proxy
with an empty string.

Infrastructure images are pinned to avoid surprise minor-version drift:

- PostgreSQL `15.18-bookworm`
- Redis `7.4.10-alpine`
- MinIO `RELEASE.2025-09-07T16-13-09Z`

Persistent data is rooted at `NOSHIRO_DATA_ROOT`, for example
`/vol1/1000/noshiro-data`, with `postgres`, `redis-broker`, `redis-cache`, and `minio`
subdirectories. Backups use `NOSHIRO_BACKUP_ROOT`, for example
`/vol1/1000/noshiro-backup`.

## Operations Scripts

- `scripts/backup_postgres.sh` writes a custom-format PostgreSQL dump and checksum.
- `scripts/restore_postgres.sh` restores a custom-format dump into a target container.
- `scripts/backup_minio.sh` mirrors MinIO data and writes file checksums.
- `scripts/restore_minio.sh` mirrors a previous MinIO backup back into the data root.
- `scripts/rehearse_migrations.sh` restores a dump into a temporary PostgreSQL and runs migrations.
- `scripts/preflight.sh` validates Compose files, Django checks, migration drift, and readiness.

Before any database change, create backups and run the rehearsal script. The
production database is never the first environment to apply new migrations.

## Build And Start

Deploy from `apps/api` inside the monorepo checkout; the compose files, the
env file, and the Docker build context all live there.

Moving an existing server from the split repositories is a one-time change: clone
`https://github.com/noshiro-5794/noshiro-db.git` (or fetch it into the existing
checkout) and run the same commands from its `apps/api` directory. If
`APP_IMAGE` is pinned in the env file, point it at `noshiro-db/api`; the old
image can then be removed with `docker image prune`.

Start infrastructure first:

```bash
cd apps/api
ENV_FILE=.env.production docker compose \
  -f docker-compose.infra.yml \
  --env-file .env.production \
  up -d --build
```

Then start the application:

```bash
ENV_FILE=.env.production docker compose \
  -f docker-compose.app.yml \
  --env-file .env.production \
  up -d --build
```

The web container may collect static files but never runs migrations automatically.
Schema changes use an explicit one-off command after the migration rehearsal below.

## Verify

```bash
ENV_FILE=.env.production docker compose \
  -f docker-compose.app.yml \
  --env-file .env.production \
  ps

ENV_FILE=.env.production docker compose \
  -f docker-compose.app.yml \
  --env-file .env.production \
  exec web python /app/src/manage.py check

curl --fail --silent https://api.noshiro.moe/api/v1/openapi/ >/dev/null
```

Inspect web, queue-specific workers, and Beat logs. Verify authentication, one public
entity read, the OpenAPI contract, and one Celery job per queue.

## Database Changes

Use expand-contract migrations. Never use production as the first migration or
backfill environment.

Before a production database change:

1. Inspect `showmigrations index users community sync ai`.
2. `scripts/backup_postgres.sh` writes a checksummed custom-format dump.
   `scripts/rehearse_migrations.sh` restores it into a throwaway PostgreSQL and
   applies every pending migration to that copy.
3. Apply migrations and run each backfill twice to verify idempotency.
4. Interrupt and resume large backfills from their stored checkpoints.
5. Reconcile entity, relation, and user-data counts against the source database.
6. Run the full PostgreSQL test suite and OpenAPI contract checks.

For a new empty database, install required extensions before the first migration:

```bash
python /app/src/manage.py bootstrap_database
python /app/src/manage.py migrate --noinput
```

After a successful rehearsal, stop Beat, workers, and other database writers. Take a
fresh backup, deploy the reviewed image, then run the one-off migration:

```bash
ENV_FILE=.env.production docker compose \
  -f docker-compose.app.yml \
  --env-file .env.production \
  run --rm web python /app/src/manage.py migrate --noinput
```

Run the rehearsed backfill and reconciliation before restarting services. Remove old
tables only in a later release after another restore rehearsal passes.

## Long-Running Sync Campaigns

A provider-wide sync is durable and sharded, so it is driven step by step rather
than by one long request. `--watch` keeps stepping until the campaign finishes and
prints one progress line per step; run it under `tmux`, because a full catalogue
takes hours at the provider's rate limit:

```bash
ENV_FILE=.env.production docker compose \
  -f docker-compose.app.yml \
  --env-file .env.production \
  exec -T web python /app/src/manage.py sync_campaign mal \
    --campaign-type full --ai-mode off --idempotency-key mal-full-1 --watch
```

Leave `--ai-mode off` for a bulk sync: AI enrichment is sampled deliberately
afterwards rather than paid for on every record. Interrupting the loop is safe —
the campaign resumes from its own work items, and a work item whose provider
answers 404 is retired instead of retried.

## Rollback

Application-only rollback uses the previous image. Never reverse a data migration
blindly; stop all writers before restoring a verified backup.
