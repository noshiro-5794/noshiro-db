# Moving the worker tier, domain by domain

The decision this plan serves is whether to move the Celery tasks off Django. It assumes
the answer is yes, in stages, and records the order and the evidence each stage needs.

The order is set by one rule: **the further a task is from the matching and provenance
engines, the earlier it can move.** Those engines are the part of the Django service layer
with the most behaviour and the least test coverage against the new schema.

## Dependency map

Read from the task modules themselves, not from the filenames.

| Task module | Tasks | Services it calls |
|---|---|---|
| `users/tasks/email_tasks` | `send_verification_email` | none — and the replacement already sends inline |
| `sync/tasks/maintenance` | `worker_heartbeat`, `scan_stale_sync_jobs`, `scan_stale_sync_states` | `incremental_sync`, `sync_job` |
| `sync/tasks/calendar` | `sync_calendar_task` | `calendar`, `sync_job` |
| `sync/tasks/airing` | `run_airing_daily_task` | `airing_daily_sync`, `sync_job` |
| `index/tasks/popularity` | `refresh_popularity_task` | `index.services` |
| `sync/tasks/frontier` | `probe_provider_frontiers_task` | `sync_job` |
| `sync/tasks/manual` | `sync_subject_by_*` | `manual_sync`, `sync_job` |
| `sync/tasks/refresh` | `refresh_bangumi_subjects_task` | `subject_refresh` |
| `sync/tasks/incremental` | `run_incremental_sync_task` | `incremental_sync`, `sync_job` |
| `sync/tasks/vndb` | `run_vndb_incremental_task`, `import_vndb_work_task` | `vndb`, `campaign`, `sync_job` |
| `sync/tasks/anilist` | `import_anilist_media_task` | `anilist`, `sync_job` |
| `sync/tasks/mal` | `import_mal_media_task`, `run_mal_season_pipeline_task` | `mal`, `mal_season_pipeline`, `sync_job` |
| `sync/tasks/campaign` | `run_sync_campaign_task` | `campaign` |
| `sync/tasks/linking` | `link_bangumi_works_task`, `recall_mal_links_task` | `bangumi_link`, `mal_link_recall` |
| `sync/tasks/matching` | `sweep_match_candidates_task` | `index.services` (matching) |
| `sync/tasks/season` | `season_pipeline`, `season_rollover`, `apply_match_proposals`, `reconcile_official_mal_links` | `season_pipeline`, `season_rollover`, `match_apply`, `index.services` |
| `ai/tasks` | `evaluate_match_candidate`, `classify_entity`, `extract_observation_evidence`, `complete_missing_schedule_slots`, `evaluate_pending_candidates` | `ai.services` (deepest coupling) |

`sync_job` appears almost everywhere: it owns the job row lifecycle the API reads back.
That makes it the first thing to port, not a task — without it no moved task can report
its own progress.

## Phases

**Phase 0 — mail.** `send_verification_email` has no service dependencies and the
replacement already sends inline. Removing it from the workers is a one-line change and
proves the queue cutover path end to end.

**Phase 1 — `sync_job`.** Port the job row lifecycle (`queued → running → succeeded /
failed`, heartbeat, reaping) to the replacement. Every later phase depends on it. Exit
criterion: a job created through the new API is driven entirely by the new code, and the
Django worker does not touch it.

**Phase 2 — maintenance and calendar.** `worker_heartbeat`, the stale-job reapers,
`sync_calendar_task`, `run_airing_daily_task`. These write rows the site reads (the
calendar board), so a shadow period is required: run both implementations against the same
provider payloads in a scratch database and diff the resulting rows.

**Phase 3 — popularity and frontier.** Read-heavy, low write surface. Verify by comparing
computed values, not rows.

**Phase 4 — provider imports.** VNDB, AniList, MAL, manual, refresh, incremental, campaign.
These share the observation/mapping pipeline, so they move together or not at all.
Verification: replay a sample of recorded observations and compare the rows written by
both implementations.

**Phase 5 — linking and season.** `bangumi_link`, `mal_link_recall`, `match_apply`,
`season_pipeline`, `season_rollover`. This is where the matching engine starts to matter.
The decision engine itself was already ported for the API (`contexts/index/resolution.py`);
the evaluation side is not.

**Phase 6 — AI.** Classification, evidence extraction, candidate evaluation, proposal
application. Deepest coupling; it also depends on the candidate pipeline from phase 5.

## What each phase must produce

- A diff of the rows written by the old and the new implementation on the same input.
- The command and the input used, kept in the PR body, not just stated as "verified".
- A rollback: the queue name flipped back, plus the migration note if columns changed.

## Why this is not scheduled yet

Any phase beyond 0 needs the stack running to record evidence, and the containers are
paused by request. Phase 0 and Phase 1 can be written without them; Phases 2–6 cannot be
verified without starting PostgreSQL, Redis and at least one worker.
