# Repository instructions

- `apps/api` uses uv, FastAPI, SQLAlchemy async, Alembic, Celery, and MCP. Run `make -C apps/api check`.
- `apps/web` uses pnpm, React, and Vite. Run `pnpm --dir apps/web check`.
- Run `make check` from the root for changes that affect both apps.

The API owns request and response shapes. Run `make openapi` and update
`apps/web/src/shared/api/` in the same change when they change. Keep the app
toolchains independent. Do not add a root Node workspace or import source
code from one app into the other.

Read the Conventions section of the relevant
[API architecture](apps/api/docs/architecture.md) or
[Web architecture](apps/web/docs/architecture.md) before moving modules.
Use Conventional Commits and explain the reason for the change in the body.
