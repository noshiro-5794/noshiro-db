# API architecture

`api.main.create_app` assembles FastAPI routes and transport middleware.
`api.config` loads settings, and `api.db` owns async sessions and parameterized
SQL execution. Mutable application state lives in PostgreSQL or Redis.

## Package ownership

| Package | Responsibility |
| --- | --- |
| `contexts/access` | Accounts, profiles, sessions, and authorization |
| `contexts/library` | Library entries, progress, tags, collections, and reviews |
| `contexts/community` | Posts, comments, follows, reactions, notifications, and moderation |
| `contexts/presentation` | Public catalogue read models, entity pages, airing data, and provenance |
| `contexts/identity` and `contexts/index` | Source identity, canonical entities, and resolution |
| `contexts/ingestion` | Provider records, observations, facts, and projected metadata |
| `contexts/synchronization` | Durable imports, campaigns, work items, and staff synchronization routes |
| `contexts/matching` | Candidate review, model evaluation, proposals, and matching routes |
| `contexts/knowledge` and `contexts/scheduling` | Evidence workflows and airing schedule policy |
| `integrations` | External provider clients and object storage |
| `worker` | Celery registration, task adapters, scheduling, and provider import orchestration |
| `mcp` | Internal proposal tools and authenticated public catalogue reads |
| `shared` | Transport problems, cursors, dispatch, timestamps, and reusable infrastructure |

## HTTP and jobs

Routes validate transport inputs, enforce access, and delegate to the owning
context. Staff import, synchronization, and matching endpoints share the
`/api/v1/operations/` prefix. Community modules own social operations.

Workers use the `realtime`, `ai`, and `sync` queues. Task entry points live under
`worker/tasks/`. `worker/app.py` registers the task modules and maintains the
broker protocol names. `worker/schedule.py` defines the periodic schedule.

External provider HTTP clients live under `integrations/providers/`.
Ingestion code owns records and projections used by imports from several
providers. [Data model](data-model.md)

## Conventions

- Name a module for its responsibility. Use the package path to carry domain context.
- Keep SQL execution in `api.db`. Keep catalogue provenance and visibility policy in the presentation context.
- Use Pydantic schemas at HTTP and tool boundaries. Keep domain policy in the context that owns it.
- Keep transactions explicit. Perform network I/O outside database locks and recheck ownership before committing results.
- Commit provider revisions, observations, and durable job state at the context boundaries that own them.
- Preserve HTTP request and response shapes, OpenAPI operation IDs, and broker task names when moving internal code.
- Use Alembic for schema changes. Write comments in English and record design decisions in commit bodies.
