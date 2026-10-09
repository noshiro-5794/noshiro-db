# Noshiro DB

A source-neutral anime and visual novel knowledge base, personal library, and
community. The Django API and the React web client live in one repository
because they ship the same contract at the same cadence.

## Layout

```text
apps/
  api/   Django, DRF, Celery, MCP entry points
  web/   React, TypeScript, Vite single-page application
```

Each app keeps its own toolchain, lockfile, and documentation:

- `apps/api/docs/` — architecture, development, deployment
- `apps/web/docs/` — architecture, development, deployment

## Quick Start

The API needs PostgreSQL, Redis, and MinIO; bring them up with the infra compose
file before the first run.

```bash
# API
cd apps/api
uv sync
docker compose -f docker-compose.infra.yml up -d
make migrate
make run            # http://127.0.0.1:8008
```

```bash
# Web client
cd apps/web
corepack enable pnpm
pnpm install
cp .env.example .env          # API_PROXY_TARGET points at the deployed API
pnpm dev                      # http://127.0.0.1:5173
```

Point the web client at a local API with `API_PROXY_TARGET=http://127.0.0.1:8008`.

## Checks

```bash
make check          # ruff + pytest + the web quality gates
make api-check      # API only
make web-check      # web only
make help
```

Both apps run the same gates in CI; `.github/workflows/` triggers each side only
when its own files change.

## Conventions

Structure and style rules are written down per app, in `docs/architecture.md`
under "Conventions". The short version: modules are named after the concern they
own, comments explain why (in English), and every app keeps its tooling local so
neither stack reaches into the other.

Commits follow Conventional Commits; `pnpm commit` inside `apps/web` walks
through the format.

## License

GNU Affero General Public License v3.0 — see [LICENSE](LICENSE). Copyright (c)
2025-2026 Noshiro_5794.

Running a modified version as a network service means offering its source to the
users of that service; section 13 of the license spells out what that requires.
