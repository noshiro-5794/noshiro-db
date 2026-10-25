# Cutover readiness

A go/no-go for retiring the Django service, written from the port's own record
rather than from optimism. The answer today is **no-go**, for four concrete reasons.

## What is already answered

| Area | Evidence |
|---|---|
| Payload parity | 137 operations compared, most field by field; `docs-parity.md` has every record |
| Writes | response bodies and the rows behind them, compared with resets in between |
| Schema | Alembic owns it; four revisions, applied and reverted on production |
| Regression | 491 of 491 comparisons matched on the latest build: 60 sampled entities across 11 list paths |
| Production install | `uv sync --no-dev` in a clean copy starts and serves (a missing `httpx` was found this way and fixed) |
| Tests | 54, none needing a database |
| Auth | password and code sign-in, registration, reset, JWT the other service accepts |

## The four blockers

### 1. Worker dispatch — closed

Import jobs now publish to the same task name the Django worker listens on
(`apps.sync.tasks.vndb.import_vndb_work_task`) through the same broker, and the job row
keeps the task id. Three tests pin the name, the arguments and the no-broker path.

The last piece was the queue. Workers run with `-Q` and the default queue is
`realtime`, so a task published without a queue sits in the broker forever. The queue
now follows the old service's routes (`apps.sync.tasks.*` → `sync`).

**Verified end to end** against the live broker: the task appeared in the `sync` queue,
was gone within seconds, and the worker logged

```
Task apps.sync.tasks.campaign.run_sync_campaign_task[623dd598…] received
```

followed by the expected `DoesNotExist` for the throwaway campaign id.

The write path was also walked once end to end: a job created through this service's
API was published, executed by the Django worker against VNDB, and read back as
`failed` with the provider's own error message. The first attempt failed differently —
the task was received and then crashed on `unexpected keyword argument 'external_id'`,
because the task names that argument after the provider (`vndb_id`).

### 2. GitHub sign-in still needs Django's signer and its cache

`social/github/start/` signs a single-use state with `django.core.signing` and records
the nonce in the shared cache; the callback verifies both. A port that signs
differently breaks the round trip.

Both endpoints are ported with their own signer. The rejected-state path is verified
(four tests on the state, plus a redirect comparison); the exchange with GitHub needs
real credentials and a real code, so it has never run. The rule the cutover must hold:
a sign-in that starts on one service has to finish on the same one.

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
