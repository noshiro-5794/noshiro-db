# Agent Notes

Two apps, two toolchains, one contract:

- `apps/api` — Django + DRF + Celery + MCP, managed with **uv**. Gates:
  `make -C apps/api check`.
- `apps/web` — React + Vite SPA, managed with **pnpm**. Gates:
  `pnpm --dir apps/web check`.
- Root: `make check` runs both.

Rules that matter when changing code:

- The API owns the payload shapes. Regenerate `apps/api/tests/snapshots/openapi.json`
  with `make openapi` and update `apps/web/src/shared/api/` in the same change.
- Keep each app's tooling local. Do not add a root Node workspace, and do not let
  the web app reach into Python sources (or the reverse).
- Naming, comment, and layering conventions are documented in each app's
  `docs/architecture.md` under "Conventions". Read the relevant one before
  renaming modules or moving files.
- Commits are Conventional Commits with a body that explains why; the commit
  history is the design record for decisions the code cannot express.
