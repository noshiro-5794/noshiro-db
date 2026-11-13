# Deployment

`compose.prod.yml` is the description of how Noshiro DB actually runs today. It was
written by reading the running containers, not by trusting the older compose files — the
infra file still says PostgreSQL 15 while the container runs 18.

It covers nine services and nothing else:

| Service | Image | Purpose |
|---|---|---|
| `api-v2` | `noshiro-db/api-v2:local` | the FastAPI replacement, published on `127.0.0.1:8010` |
| `worker-realtime` | `noshiro-db/api:prod` | Celery `-Q realtime` |
| `worker-ai` | `noshiro-db/api:prod` | Celery `-Q ai` |
| `worker-sync` | `noshiro-db/api:prod` | Celery `-Q sync` |
| `beat` | `noshiro-db/api:prod` | Celery beat |
| `postgres` | `postgres:18-bookworm` | `127.0.0.1:5433` |
| `redis-broker` / `redis-cache` | `redis:7.4.10-alpine` | `127.0.0.1:6380` / `6381` |
| `minio` | `minio/minio:RELEASE.2025-09-07T16-13-09Z` | `127.0.0.1:9000`, console `9001` |

The Django **web** service is absent on purpose: it was retired when the FastAPI service
took the proxy. The Django image stays because its Celery workers still run the sync, AI
and scheduled jobs.

## Check it without changing anything

```sh
cd /vol1/1000/projects/noshiro-db/api-v2-build
E=/vol1/1000/projects/noshiro-db/app/apps/api/.env.production
ENV_FILE=$E docker compose -p noshiro-db -f deploy/compose.prod.yml --env-file "$E" config
```

Always pass `-p noshiro-db` and `--env-file`: the project name is what keeps this from
creating a second copy of the stack, and the env file is what the required variables
(`POSTGRES_PASSWORD`, `MINIO_ROOT_PASSWORD`) are interpolated from.

## Things that are easy to get wrong

**PostgreSQL 18 mounts the parent, not `data`.** The image keeps `PGDATA` one level
deeper, so the volume is `…/postgres18:/var/lib/postgresql`. The older infra file mounts
`/var/lib/postgresql/data` and runs 15; those two data directories are not
interchangeable in either direction.

**The env file lives in the `app` checkout**, not next to this compose file:
`…/app/apps/api/.env.production`. `api-v2-build` has no `apps/api/` directory, which is
why the older api-v2 compose file's `../api/.env.production` default never worked there.

**`NOSHIRO_DATA_ROOT` may already be set in that env file.** When it is, it wins over the
default in this compose file — today it points at `/vol1/1000/noshiro-data`, the
compatibility symlink to `services/noshiro-db/data`. The symlink must be updated or the
env file changed before the link is removed.

## Not in this file yet

- **MCP**: the older app compose has an `mcp` profile that publishes container port 8010
  on the host. Sharing that host port with `api-v2` is why the migration notes reserve a
  separate `MCP_HOST_PORT` (default `8013`); the service is not part of today's
  deployment, so it is not reproduced here.
- **`migrate`**: a one-shot profile in the app compose. The replacement service carries
  its own Alembic migrations (`alembic upgrade head` inside the `api-v2` image), so the
  Django `migrate` profile only matters while the Django workers still own their schema.
- **Django web**: retired, not described.

## Restoring a paused stack

The services are stopped, not removed. Start the data tier first, then the app tier:

```sh
docker start noshiro-db-postgres-1 noshiro-db-redis-broker-1 noshiro-db-redis-cache-1 noshiro-db-minio-1
docker start noshiro-db-api-v2-1 noshiro-db-worker-sync-1 noshiro-db-worker-ai-1 \
              noshiro-db-worker-realtime-1 noshiro-db-beat-1
```
