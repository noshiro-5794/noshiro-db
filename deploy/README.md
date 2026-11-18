# Deployment

The production manifest defines one application image for the FastAPI service,
three Celery workers, beat and the authenticated public MCP service. PostgreSQL,
Redis broker/cache and MinIO keep their existing persistent storage locations.

Build the application from `apps/api/Dockerfile` using `apps/api` as the context.
Set `APP_IMAGE`, `APP_IMAGE_TAG` and `ENV_FILE` when validating the manifest.
`API_PORT` defaults to 8010 and `MCP_PUBLIC_PORT` defaults to 8011. Both host
ports bind to loopback for the reverse proxy. MCP requires the existing signing
secret and active user access tokens.

Apply Alembic migrations with the application image before starting application
services. Start `api`, `worker-realtime`, `worker-ai`, `worker-sync`, `beat` and
`mcp` from this manifest. The three worker queues preserve their separate
concurrency settings. Beat uses its expiring Redis heartbeat for readiness.

The local source has been consolidated into `apps/api`. Production rollout and
post-deployment verification remain pending. The pre-migration database, object
storage and environment backups are retained outside the repository.
