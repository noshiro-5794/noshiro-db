# The worker tier: what is left of Django

`api.noshiro.moe` is served by the replacement and the Django **web** container is gone.
What still runs Django code is the task runtime: three Celery workers and beat, using the
`noshiro-db/api:prod` image.

This page records what that tier is, so the decision to move it — or not — is made
against numbers rather than a sense of "almost done".

## What is in it

| Measure | Value |
|---|---|
| `@shared_task` definitions | 30 |
| Beat schedule entries | 18 |
| Task module lines | ~1,600 |
| Service layer they call | ~17,400 lines across `sync`, `ai`, `index`, `users` |
| Whole Django app tree | ~48,000 lines |

The tasks:

- **sync** — VNDB, AniList and MAL imports; Bangumi subject refresh; season and calendar
  pipelines; incremental sync; frontier probing; link reconciliation; match candidate
  sweeps; stale-job reaping.
- **ai** — observation evidence extraction, entity classification, match evaluation,
  proposal application.
- **users** — the verification mail task (already superseded by the replacement's inline
  sender, and still present).

## Why this is not "the API port, continued"

The workers do not serve HTTP. They call the Django ORM directly through the same service
layer the retired web service used. Moving them means porting that service layer to
SQLAlchemy — catalogue, matching, provenance and AI policy logic — not porting routes.

The replacement currently **publishes to** these workers: `apps.sync.tasks.*` on the
`sync` queue, `apps.ai.tasks.*` on `ai`. That was verified end to end: a job created
through the new API was executed by the Django worker and its failure written back.

## Options, with what each costs

1. **Keep the task tier on Django** (today). Nothing to build. Django remains as a task
   runtime with no HTTP surface, which is a normal deployment shape: a job runner that
   shares the database.
2. **Move tasks one domain at a time.** Start with the ones that do not need the matching
   or provenance engines: calendar refresh, airing board, popularity, frontier probing.
   Each move needs a shadow period because these tasks write rows.
3. **Move the whole service layer.** Not a task-level port; it is the larger half of the
   original codebase. It would also move the candidate-decision engine, which was ported
   to the replacement precisely because its API asked for it.

## What is worth doing before any of this

The deployment is described by `deploy/compose.prod.yml`, which keeps the Django image for
exactly this tier. Any move renames that image's role from "the old API and its workers"
to "the task runner", and the compose file is where that should become visible.

Until then: the API objective is met, and the worker tier is a deliberate, working part of
the system rather than a leftover.
