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

## The next block

The community timelines (`me/activities`, `activities`, `me/feed`) share one
missing piece: a **target dispatcher** — `(target_type, target_id) → summary` for
post, comment, review, collection and activity. The activity target is already
implemented in `community/notifications.py` and can be generalised. Build it once,
then port the three timelines and the remaining comment/post endpoints on top.
