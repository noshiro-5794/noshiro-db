# Status

A snapshot of the replacement service after the long porting run. It is not a plan; the plan is in
`docs-display.md`, `docs-schema.md` and `docs-parity.md`.

## Covered endpoints

One hundred and thirty-seven operations compared with the Django response. The table below is the
shape of the coverage; `docs-parity.md` has every recorded comparison.

| Area | Endpoints | Evidence |
|---|---|---|
| catalogue | `collections/`, `collections/{slug}/entities/`, `entities/` with its filters | `docs-parity.md`, 8 + 4 variants |
| entity | `entities/{id}/`, `metrics/`, `relations/`, `credits/`, `releases/`, `characters/`, `episodes/`, `evidence/` | `docs-parity.md`, shadow runs |
| calendar | `calendar/events/` — board, range, timezone, works | `docs-parity.md`, 5 variants |
| auth | `auth/social/providers/`, `auth/sessions/password/`, `auth/session/`, `users/me/profile/`, `users/me/settings/` | `docs-parity.md` |
| community | notifications, blocks, mutes, follows, bookmarks, reactions, reports (write, staff queue, resolution), posts (list, detail, write, moderation), comments (list, write, moderation), all four timelines | `docs-parity.md` |
| collections | public list, mine (list, create, detail, edit, delete), items (list, add, edit, delete, replace) | `docs-parity.md` |
| operations | import jobs (list, detail, create), sync campaigns (list, detail, create, items, claims, summary), matching candidates (list) | `docs-parity.md` |
| library | tags (list, create, rename, delete), entries (list, read, add, update, delete), release states, rating details, reviews (list, write), yearly stats | `docs-parity.md` |

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
