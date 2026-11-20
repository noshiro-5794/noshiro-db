# System architecture

Noshiro DB has two independently built applications linked by the versioned
HTTP contract. Both live in the same repository so a change to an API payload
and its browser decoder can be reviewed and shipped together.

| Layer | Responsibility |
| --- | --- |
| Web | React SPA, route composition, interaction state, and API decoding |
| API | FastAPI HTTP endpoints, authorization, and application services |
| Data | PostgreSQL tables, Alembic revisions, and S3-compatible media |
| Jobs | Celery workers and scheduler, backed by Redis |
| MCP | Internal knowledge tools and authenticated public read tools |

## Request and job flow

The Web app calls `/api/v1/` and decodes responses at its transport boundary.
API routes validate requests and call context-owned services. Those services use
SQLAlchemy async sessions and commit at explicit transaction boundaries.

Provider clients fetch source data. Ingestion stores source revisions and
observations, then updates canonical entities and presentation data. Staff
operations enqueue durable work for the appropriate queue. Workers record job
results in PostgreSQL and can retry leased work after an interruption.

The same API image supplies the HTTP service, workers, scheduler, and public MCP
service. The Web build emits static assets for a separate frontend host.

## Application boundaries

The Web app depends on HTTP payloads and its own typed client. The API owns the
OpenAPI schema, database migrations, provider adapters, and job messages. Root
Make targets delegate to the app-local toolchains.

[API architecture](../apps/api/docs/architecture.md) · [Web architecture](../apps/web/docs/architecture.md)
