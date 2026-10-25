# Cutover readiness

A go/no-go for retiring the Django service, written from the port's own record
rather than from optimism. The answer today is **no-go**, for four concrete reasons.

## What is already answered

| Area | Evidence |
|---|---|
| Payload parity | 137 operations compared, most field by field; `docs-parity.md` has every record |
| Writes | response bodies and the rows behind them, compared with resets in between |
| Schema | Alembic owns it; four revisions, applied and reverted on production |
| Regression | a randomised shadow run over 75 list paths |
| Tests | 54, none needing a database |
| Auth | password and code sign-in, registration, reset, JWT the other service accepts |

## The four blockers

### 1. Worker dispatch is not ported

`POST /operations/import-jobs/` and `POST /operations/sync/` write the row and answer
202, but nothing picks the job up. Django's worker does. Until this moves, those two
endpoints look healthy and do nothing.

*What closing it means:* either port the tasks, or point the new service at the same
broker and publish with matching task names. The second is cheaper and keeps one worker.

### 2. GitHub sign-in still needs Django's signer and its cache

`social/github/start/` signs a single-use state with `django.core.signing` and records
the nonce in the shared cache; the callback verifies both. A port that signs
differently breaks the round trip.

*What closing it means:* reproduce the signer (verifiable against Django's own
`signing.loads`) and write the same cache key, or move both endpoints together.

### 3. The candidate decision drives the resolution engine

Recorded in `docs-transition.md`: a `bind` merges entities and rebuilds the fact layer.
This is the engine, not the API. It stays until the engine moves.

### 4. Two smaller ones

- The verification mail body is shorter than the branded template (subject and code match).
- `parity.py` has `PARITY_DEBUG` now, but its output format still reads `old != new`,
  which cost a round when it was read backwards.

## What a cutover would need

1. One worker, one broker, both services publishing to it — otherwise the write
   endpoints are half alive.
2. OAuth either ported whole or explicitly still served by Django behind the same host.
3. A shadow period on the write paths: the read comparison is strong, the write
   comparison is per-call and not continuous.
4. A rollback that does not depend on the database migrating back: the new service
   only ever reads and writes the shared schema, so pointing the host back at Django
   must remain possible until the engine moves.

## Why writing this down matters

Every item above is already in the record; none of it is new work. The value is that a
go/no-go can be argued from evidence instead of from how the port feels, and that the
first item — a worker nobody notices is missing — cannot hide behind 137 green endpoints.
