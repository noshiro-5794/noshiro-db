# Handoff

What a new session needs to know that the code does not say.

## Where things stand

- **33 endpoints** answer identically to the Django service: the catalogue and the
  entity satellites, the calendar and the board, auth (login, logout, social list,
  profile, settings), and the community block/mute/follow/notification basics.
- **Schema is Alembic's**: four revisions, all applied and reverted on production.
- **The display layer works end to end**: bundle → rule generator → validator →
  draft → activation → the summary reads the active profile, proven with a probe.
- **~90 operations remain**, listed in `docs-coverage.md` with sizes and an order.

## Conventions that are not optional

- One branch per pull request, cut from `origin/main` **after** the previous merge.
  Reusing a merged branch makes the PR `dirty` and its checks never start.
- Every endpoint comes with a comparison: `parity.py` for reads and POSTs,
  `state_parity.py` for writes (same seed, both services, compare rows), `shadow.py`
  for a regression sweep.
- Run `make -C apps/api-v2 check` before pushing: ruff, `ruff format --check`,
  `mypy --strict`, pytest. `UV_CACHE_DIR=/tmp/uv-cache` on this machine.
- Docs live next to the code: `docs-parity.md` (evidence), `docs-display.md`,
  `docs-schema.md`, `docs-transition.md`, `docs-coverage.md`.

## Running the tools

`parity.py` and `shadow.py` import each other, and `shadow.py` samples entities from
the database, so both need two things from the worktree:

```sh
PYTHONPATH=. DATABASE_URL=postgresql://… uv run python scripts/shadow.py \
  --old http://127.0.0.1:8008 --new http://127.0.0.1:8010 --count 60
```

`shadow.py` has no `--ignore`: `trace_id` is already dropped inside it. `parity.py`
does, and `PARITY_DEBUG=1` prints the URL each side is asked for.

## Traps this port has already hit

| Trap | What happens |
|---|---|
| `UPDATE`/`DELETE` without `RETURNING` | the row helper raises `ResourceClosedError` |
| a stale uvicorn | the code is fixed, the probe still fails; restart after every deploy |
| `cd /tmp` before git | the commit silently lands in the wrong directory, or not at all |
| a cursor built from the extra row | the body matches and only the decoded `next` differs |
| `CAST(:id AS bigint)` with a string | asyncpg rejects it; convert in Python |
| DRF's `allow_null` | an absent field renders as `null`, not as a missing key |
| the calendar's work summary | built even when not returned: it decides visibility and hides adult works |

## What the port has already built to reuse

| Piece | Where | Used by |
|---|---|---|
| paginated envelope | `shared/pagination.py` | every list endpoint |
| timeline cursor | `shared/cursor.py` | notifications, next the timelines |
| identity resolution | `presentation/identity.py` | calendar and board |
| problem bodies | `shared/problems.py` | every failure |
| target shapes | `community/targets.py` | notifications, bookmarks |
| bookmark summaries | `community/targets.py` | the bookmark list and write |
| **visibility rules** | `community/visibility.py` | bookmarks, reports, reactions next |

The visibility module is the one that mattered most: "the target exists" and
"the caller may see it" are different questions, and Django answers the second
with the same 404 as the first so a private target cannot be probed.

## Running the tools

`parity.py` and `shadow.py` import each other, and `shadow.py` samples entities from
the database, so both need two things from the worktree:

```sh
PYTHONPATH=. DATABASE_URL=postgresql://… uv run python scripts/shadow.py \
  --old http://127.0.0.1:8008 --new http://127.0.0.1:8010 --count 60
```

`shadow.py` has no `--ignore`: `trace_id` is already dropped inside it. `parity.py`
does, and `PARITY_DEBUG=1` prints the URL each side is asked for.

## Traps this port has already hit

Each of these cost a round; none of them is obvious from the Django code alone.

| Trap | What happens | Fix |
|---|---|---|
| Literal route vs id route | `/users/me/…` and `/operations/sync/summary/` are parsed as ids | register the literal route first |
| Reserved column name | `user_collection_item."order"` must be quoted in the column list | quote it, qualified references are fine |
| `metadata` is NOT NULL with no default | post, comment, moderation and profile inserts 500 | supply `'{}'::jsonb` |
| `user_profile` has four more NOT NULL columns | register 500s | `#7F6FB0`, `auto`, `auto`, `false` |
| A serializer field is not a column | `provider_record` is `provider_record_id` | alias in the SQL |
| `WHERE` inside subqueries | splitting a query on `WHERE` cuts too early | replace the one clause instead |
| Time-derived fields | `eta_seconds`, throughput differ every run | ignore them in the comparison, do not "fix" them |
| Diff direction | `status 404 != 200` means **old** is 404 | read it twice before blaming the tool |
| Adding what already exists | `/health/live` was there; a rewrite nearly broke it | grep the route before writing one |
| Paths from memory | three "failures" in a sweep were paths that never existed | read the route table, not my recollection |
| A gate that does not cover the code | a syntax error in `scripts/` passed CI | lint every directory you ship, not just `src` |
| A task published to the default queue | it sits in the broker forever; the endpoint still answers 202 | workers run with `-Q`; routing lives in the settings |

## Django crashes on legal writes

Five are recorded in `docs-parity.md`: an inverted watch-date range, a valid
release state, tag replacement, rating details, and one more. Each answers 500
from the old service where this one answers 400 or 200. They are recorded, not
reproduced — a 500 is not a contract. This is also the argument for the rewrite.

## The next block

The community timelines (`me/activities`, `activities`, `me/feed`) share one
missing piece: a **target dispatcher** — `(target_type, target_id) → summary` for
post, comment, review, collection and activity. The activity target is already
implemented in `community/notifications.py` and can be generalised. Build it once,
then port the three timelines and the remaining comment/post endpoints on top.

## Step zero

`git fetch origin main` before cutting the branch. A merge through the API does
not move the local `origin/main`, so a branch cut right after a merge starts from
the commit before it — and the import it needs is missing.
