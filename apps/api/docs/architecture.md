# Architecture

The API uses FastAPI, SQLAlchemy 2 async sessions, Alembic, Pydantic v2,
PostgreSQL, Redis, Celery and S3-compatible object storage.

The `api` package contains application configuration and HTTP assembly.
`contexts` groups access, identity, library, community, presentation, matching,
knowledge, scheduling and synchronization responsibilities. `worker` owns provider
adapters, import execution and Celery entry points. `mcp` owns protocol adapters.
`shared` contains common transport, inference, pagination and dispatch support.

## Conventions

Name modules for their responsibility. Keep pure policy in domain modules and
I/O in application services and read models. Routes translate HTTP inputs and
responses. Reuse context-owned services across HTTP, workers and MCP.
Use explicit types, readable SQL parameters and short transactions. Keep network
requests outside database locks and recheck ownership before durable writes.
Comments explain decisions in English. Each app owns its toolchain and dependencies.
Alembic owns schema changes. Conventional Commit bodies record design decisions.

## Knowledge Model

```text
Entity
|- Work
|  |- AnimeProfile
|  `- GalgameProfile
|- Release
|- Episode
|- Contributor (Person or Organization)
`- Character
```

`Entity` is the stable UUID, visibility, lifecycle, and redirect anchor. `Work` is a
creative work. Platform, language, regional, and limited editions are Releases;
sequels, independent seasons, OVAs, fandiscs, and materially different remakes are
separate Works. Anime and Galgame enter the primary Index collections; other works
remain searchable related entities.

Names retain language, script, region, kind, and provenance. Partial dates retain
their precision and raw value. Adult and spoiler visibility belongs to the affected
entity, description, fact, or media rather than being inferred at response time.
Core relations use typed models; `Fact` is reserved for long-tail knowledge.

## Provider Data Flow

Bangumi and VNDB are peer providers. Neither wins because it was imported first.

```text
ProviderRevision -> MappingRun -> Observation -> evidence
                                             -> resolution -> API projection
ProviderRecord <-> ProviderRepresentation <-> Entity
```

Raw revisions and normalized observations are immutable and mapper-versioned. Metrics
remain separate by provider and observation time. Resolver policy chooses rebuildable
projections without deleting conflicting source values. Merges use redirects so they
remain reversible and evidence is retained.

## AI And MCP

AI produces structured proposals and cannot write canonical tables directly.
`contexts/knowledge` owns the durable harness, versioned Skills, typed Tools, policy, evidence,
and audit; `integrations.ai` isolates vendor clients. A run is persisted as
`AgentRun -> AgentStep -> AIRun/ToolInvocation -> SourceArtifact/AIClaim`.
The database is the execution source of truth; checkpoints are immutable snapshots,
and retries use explicit state transitions and idempotency scopes. Apply, approval,
and validation steps fail closed until a concrete handler is registered.

Open-ended retrieval tasks run on a second runtime mode: an append-only
`AgentMessage` transcript drives a native tool-calling loop until the model
returns a final answer. The loop reuses the same tool registry, permission
scopes, budget, and evidence capture as deterministic workflows, so decision
skills stay bounded while recall skills (for example Bangumi↔MAL candidate
discovery) may search the database and external APIs iteratively before the
adjudicator decides.

Provider-wide synchronization is linked to one `AgentRun` through `SyncCampaign`.
Fetch, pagination, mapping, and revision writes remain deterministic and resumable;
AI is invoked only at explicit normalization/enrichment boundaries with an
`Observation` or `SourceArtifact` attached. AI output is a claim/proposal and needs
policy review before canonical projection. `SyncWorkItem` leases make duplicate
Celery delivery and worker interruption recoverable; a campaign is not considered
complete while discovery pages or queued work items remain.

The anime calendar keeps one active **airing board** (the current on-air season)
instead of accumulating quarterly rows: calendar refreshes replace the board in
place and archive the window on season rollover, while each work keeps its own
per-episode airing facts. The board feeds a durable `airing_daily` queue that
refreshes current-season subjects and episodes in bounded batches.

The internal MCP server exposes reads and audited proposal submission; the public
server exposes only authenticated, rate-limited safe projections. MCP tools and
in-process tools share the same namespaced, Pydantic-validated registry and explicit
permission scopes.

External HTTP clients use `OUTBOUND_PROXY_URL` when configured. Set it on servers
that cannot reach Bangumi, VNDB, image hosts, Resend, hCaptcha, or the AI provider
directly. Internal service names in `OUTBOUND_NO_PROXY_HOSTS` should remain excluded
from the proxy. On the current server, the v2raya plain HTTP inbound listens on
`192.168.3.222:7890`; use that as `OUTBOUND_PROXY_URL`.

## Public API

The public REST root is `/api/v1/`, assembled by `api.main.create_app`.
OpenAPI is served at `/api/v1/openapi/` and exported by `make openapi` into
`tests/snapshots/openapi.json`. The web app owns its matching TypeScript client.

Alembic owns the application schema. Production still contains framework support
tables awaiting dependency and data checks before retirement. Session blacklist
records remain active application data. Production changes follow the root
[deployment guide](../../../deploy/README.md).
