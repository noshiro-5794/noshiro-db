# Status

A snapshot of the replacement service. It is not a plan; the plan is in
`docs-display.md`, `docs-schema.md` and `docs-parity.md`.

## Covered endpoints

Eleven entity and catalogue endpoints plus the auth list and the calendar, each
compared with the Django response:

| Area | Endpoints | Evidence |
|---|---|---|
| catalogue | `collections/`, `collections/{slug}/entities/`, `entities/` with its filters | `docs-parity.md`, 8 + 4 variants |
| entity | `entities/{id}/`, `metrics/`, `relations/`, `credits/`, `releases/`, `characters/`, `episodes/`, `evidence/` | `docs-parity.md`, shadow runs |
| calendar | `calendar/events/` — board, range, timezone, works | `docs-parity.md`, 5 variants |
| auth | `auth/social/providers/`, `auth/sessions/password/`, `auth/session/`, `users/me/profile/`, `users/me/settings/` | `docs-parity.md` |
| community | notifications (count, read-all), blocks (write, list), mutes (list), follows (write, lists) | `docs-parity.md` |

`scripts/parity.py` compares named paths; `scripts/shadow.py` samples entities and
walks every entity endpoint plus the list paths. Last shadow run: **103/103**.

## Beyond parity

- **Display layer**: bundle, rule generator, validator, drafts, activation, the
  reader switch and a probe that proves it — `docs-display.md`.
- **Schema ownership**: Alembic is the only place DDL is written, with four
  revisions applied and reverted on production — `docs-schema.md`.
- **Signals**: `metric_current`, `metric_daily` and `entity_metric_current`,
  backfilled from `metric_snapshot` with exact counts.

## Not started

`docs-coverage.md` lists every remaining operation path by path, with a size
estimate and the order to take them in.

| Item | Why it waits |
|---|---|
| `calendar/board/events/` | the Gantt projection: its own round |
| auth login and registration | needs a password hasher compatible with Django and a test account |
| library, collections, reviews (writes) | need authentication first |
| ingestion (providers, mappers, sync) | the largest remaining block; nothing else depends on it for reads |
| decommissioning Django | last step, after every endpoint and the sync path move |

## Transition affordances

`docs-transition.md` lists what exists only because Django still runs — the
password verifier, the `hash_password` claim, the forwarded-proto reading — and
what removes each one. None of it is the target design.

## How to verify

```bash
make -C apps/api-v2 check      # ruff, mypy --strict, tests
uv run python -m scripts.parity --old ... --new ... --path ...
DATABASE_URL=... uv run python -m scripts.shadow --old ... --new ... --count 20
```
