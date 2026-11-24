# Noshiro DB API

The API owns catalogue queries, account and library operations, community
features, provider ingestion, and background jobs. The package uses FastAPI,
Pydantic v2, SQLAlchemy async sessions, Alembic, Celery, and MCP.

| Command | Purpose |
| --- | --- |
| `make sync` | Install the locked Python environment |
| `make migrate` | Upgrade the configured database |
| `make run` | Start HTTP on `127.0.0.1:8008` |
| `make check` | Run lint, types, contract inventories, and tests |
| `make openapi` | Export the versioned OpenAPI snapshot |

- [Development](docs/development.md) covers local services, environment, and tests.
- [Architecture](docs/architecture.md) explains package boundaries and conventions.
- [Data model](docs/data-model.md) describes catalogue identity and source evidence.
- [Database dictionary](docs/data-dictionary.md) describes every application table with examples.
- [Migrations](docs/migration.md) covers fresh databases and existing deployments.
- [Deployment](../../deploy/README.md) describes the production services.
