   815ed15..49eb233  main       -> origin/main
   1d345c9..65a85fd  main       -> origin/main
# Worker migration: what is done, and where the evidence is

This is the running ledger for moving the Celery tier off Django. Each entry names the code
and the comparison or run that backs it, because "ported" without evidence is a claim, not a
result.

## Done

| Piece | Code | Evidence |
|---|---|---|
| Provider transport (proxy, error taxonomy, absolute-URL guard) | `worker/providers/http.py`, `errors.py` | 11 offline tests through `httpx.MockTransport` |
| VNDB client | `worker/providers/vndb.py` | same suite: empty result is a terminal 404, storage policy blocks |
| MAL client (client id, bounded retries, frontier-bounded discovery) | `worker/providers/mal.py` | 11 tests: retry-then-success, back-off precedence, exhausted budget |
| Frontier probe | `worker/frontier.py` | 7 tests: run of misses ends the space, provider error is not a miss |
| Job lifecycle (`sync_job`) | `worker/jobs.py` | exercised end to end by the MAL import run |
| Record + revision | `worker/records.py` | real DB run: repeat payload makes no revision |
| Observation + mapping run | `worker/ingestion.py` | real DB run: repeat observation deduplicates |
| Entity + work mapping | `worker/entities.py` | real DB run: repeat import reuses the entity |
| Names, description, artwork, membership | `worker/presentation.py` | real DB run: 2 names then 0, media 2 then 0 |
| Anime profile, external link, metrics | `worker/profiles.py`, `worker/metrics.py` | real DB run; metric keyed on the observation time |
| Facts + evidence + decision rebuild | `worker/facts.py` | real DB run: same value → same fact, one decision |
| MAL importer | `worker/mal_import.py` | real DB run + **shadow comparison** below |
| Mal import task | `worker/tasks.py` | same name, queue and lifecycle as the Django task |
| Official MAL id reconciliation | `worker/mal_identity.py` | read-only parity with Django at 200 and 5,000 records; synthetic pending pair merged and rolled back (1 redirect, 1 merge event, source `merged`, 1 decision) |
| Calendar board replacement | `worker/calendar.py`, `calendar_write.py`, `calendar_lookup.py`, `calendar_sync.py` | driven end to end by the stored Bangumi payload: 112 items → 108 events, one board archived and one created, rolled back; the previous-calendar lookup matches Django at 112 ids |
| Bangumi subject import | `worker/subject_mapping.py`, `subject_import.py` | real payload re-imported: every delta zero (dedupe parity); synthetic subject creates 1 entity, 1 work, 2 names, 1 description, 2 images, 1 profile, 7 facts |
| Bangumi subject refresh | `worker/subject_refresh.py` | target selection identical to Django at `limit=50`, including order and legacy-first |
| AniList import | `worker/anilist_import.py` | names, description, artwork, profile and 11 facts including `anilist-id-mal`, all rolled back |
| Airing daily refresh | `worker/airing_daily.py` | target selection identical to Django (282 targets, same order); window transitions exercised on the real state table: running refuses a second claim, finish idles, failure counts |
| Matching baseline | `scripts/capture_matching_baseline.py` | read-only snapshot of what the old matcher produced: totals by policy and status, 200-row sample, digest `885601929d9d109a` |

A registration floor (`MIN_REGISTERED`) now fails the build when the count drops: a deleted
registration has no other symptom. It was added after a stale-checkout rebase silently
removed 171 lines of task registrations, taking the count from 8 to 5 without any failing
check.

The denominator moved from 23 to 30 when the coverage tool learned to read multi-line
decorators — the earlier figure was an undercount, so the percentage was too generous.

## Runtime, verified in containers

The worker was started from the production compose against the rebuilt image and consumed
a real message from the `sync` queue:

```
Task apps.sync.tasks.maintenance.scan_stale_sync_jobs received
Task apps.sync.tasks.maintenance.scan_stale_sync_jobs succeeded in 0.06s: {'stale_jobs': 0}
sync queue: 0
```

Two failures surfaced only here, both silent in every other kind of check:

* the engine was created once per process, so the **second** task died with
  `attached to a different loop` — each Celery task gets a fresh event loop;
* the worker listened on `realtime` while routing published to `sync`, so the message sat
  unread. Both are now covered by checks in `scripts/` that run in CI.

## The shadow comparison that has been run

Same fixture payload through the Django importer and through the port, one transaction per
side, both rolled back. Compared: names, descriptions, media, work type, profile, links,
facts, metrics.

Result: **all equal**, after the comparison found one real divergence — Django uppercases
the media type (`TV`), the port was storing `tv`. Nothing else differed.

Reproduce it with `scripts/shadow_import.sh` (fixture in `scripts/fixtures/mal_anime.json`).

## How far along

`python scripts/task_coverage.py` prints the number: **10 of 30 tasks**, counting only the
names the replacement actually registers under a Django task name. Refresh it from the
tool rather than from memory — the first estimates in this ledger were made by counting
decorator lines and overstated the total.

## Not done

Counted from the task modules' own imports:

| Group | Tasks | Notes |
|---|---|---|
| AniList client and importer | 1 import task | needs the GraphQL client and its mapper |
| Bangumi client and importer | refresh, link, manual sync | needs the client and the subject mapper |
| Campaign, incremental, frontier task | 4 tasks | depend on the importers above |
| Calendar and airing | 2 tasks | write the board the site reads |
| Linking and season | 6 tasks | depend on the matching engine |
| AI | 5 tasks | deepest coupling |

The MAL path proves the pattern; the remaining work is repetition of it with more provider
specifics, plus the matching engine for the last two groups.

## Rules this ledger follows

1. A write path is "done" only after it has run against the real schema — three of the
   write modules failed on first execution (UUID keys without defaults, NOT NULL columns,
   partial unique indexes) after passing a column-by-column read.
2. A moved task ships with a comparison against the old implementation, not just a test.
3. Anything unverified is written down as unverified rather than omitted.

## Which task is actually next — and why the tables below are a warning

Two measurements were taken and they **contradict each other**, which is the useful result:

| Task | Direct file | Transitive closure |
|---|---:|---:|
| `check_season_rollover_task` | 110 lines | **9,824 lines / 47 files** |
| `sweep_match_candidates_task` | 774 lines | 96 lines / 2 files |
| `import_mal_media_task` (done) | 361 lines | 2,538 lines / 17 files |
| `run_vndb_incremental_task` | 2,485 lines | 9,153 lines / 37 files |

Neither number is trustworthy on its own:

* The direct-file size misses orchestration. `check_season_rollover` is 110 lines of code
  that calls four services (season pipeline, MAL schedule, AniList season, calendar sync) —
  by transitive size it is the **largest** remaining task, not the smallest.
* The static-import closure misses indirection. `sweep_match_candidates` shows 96 lines
  because it imports `apps.index.services`, a re-export package rather than the modules
  that do the work.

**Do not schedule from either table.** The only dependable size signal here is the one
finished task: `import_mal_media_task` needed ~2,500 lines of closure behind it, a client,
a fixture, a real-database run and a shadow comparison. Assume the remaining tasks are of
that order and pick by *reading what the task calls*, not by a line count.

## What the next unlock actually is

Three remaining tasks share one missing dependency, and it is not the matching engine:

`sync_calendar_task` with `sync_subject_details=True`, `run_airing_daily_task`, and
`refresh_bangumi_subjects_task` all need **Bangumi subject import**
(`apps/sync/services/subject.py::upsert_subject`, 243 lines) — the step that turns a
Bangumi subject into a work entity with its names, description and profile.

So the order is not "airing daily next because it is adjacent": it is **subject import
first**, and the other three follow from it. That module is also what the calendar board
currently works around by skipping subjects the catalogue does not hold.

## The task to take next

`reconcile_official_mal_links_task` — 271 lines in `apps/index/services/mal_identity.py`,
and the reasons are specific rather than size-based:

* it is **database-only**: it reads AniList records for an official MAL id, finds the MAL
  record for that id, and binds the pair. No HTTP client, no new provider surface.
* the hard part it depends on — `entity_resolution_service.merge`, with the redirect,
  the lifecycle change and the fact rebuild — is **already ported and verified** in
  `contexts/index/resolution.py`, including the shadow run against Django.
* its output is inspectable: a count of pairs bound, and the rows in `entity_redirect`
  and `entity_merge_event` can be diffed against a Django run on the same sample.

Everything after it needs either a new provider client (AniList, Bangumi) or the matching
engine (candidate sweep, season pipeline, AI), which is why those stay untouched for now.

## Calendar write contract (found, not guessed)

The parse layer is done (`worker/calendar.py`). What the write layer must respect, read
from the live schema:

**`airing_board`** — `season_key`, `status`, `item_count`, `metadata` (jsonb),
`effective_from`, `effective_until`, `observation_id`. There is a **partial unique index on
`status = 'active'`**, so only one active board can exist: replacing the board means
flipping the old row before inserting the new one, inside one transaction.

**`airing_event`** — `work_id` and `collection_doing` are required; `starts_at`,
`episode_entity_id` and `weekday` are nullable; `timezone`, `region`, `precision` and
`raw_value` are required. Its uniqueness includes **`observation_id`**, so the same event
recorded under two observations is two rows — history is preserved on purpose, and
"current" is decided by the board's observation rather than by deleting old rows.

Two consequences worth stating before writing code:

* a board swap cannot be two independent inserts — the partial unique index rejects the
  second active row;
* the diff against the previous calendar is a *report*, not a delete: previous rows stay,
  and `previous_calendar_item_ids` reads them back through the last calendar observation.

## Starting the next task

The MAL path is the template. Copying it is the cheapest way to add a provider:

1. **Branch from a freshly fetched main.** On the deployment host the checkout's
   `origin/main` ref is stale right after a merge, so `git fetch origin main` first and
   branch from `origin/main` — never from a ref that was fetched earlier in the same
   session. A branch cut from a squash-merged commit shows up as `dirty` and cannot merge.
2. **Client first, transport underneath.** `worker/providers/http.py` already classifies
   failures and applies the proxy; a new client only adds its request shape, its id
   conventions and its storage-policy check.
3. **Write path.** `records.record_payload` → `ingestion.record_observation` →
   `entities.map_work` → `presentation.*` → `profiles.*` → `metrics.record_metrics` →
   `facts.record_fact`. These have all run against the real schema; reuse them rather than
   writing new SQL.
4. **Run it, do not read it.** `scripts/verify_ingestion.py` runs the whole cycle inside one
   transaction and rolls back. Add the new provider's section there. Three write modules
   failed on first execution after passing a column-by-column read.
5. **Shadow it.** Run the Django importer and the port on the same fixture payload, one
   transaction per side, both rolled back; diff names, descriptions, media, work type,
   profile, links, facts and metrics. That comparison is what caught the `TV`/`tv` case.
6. **Then register the task** under the Django name on the Django queue, so either worker
   can consume the message.

## Traps already paid for

- These tables have **no database default** for their UUID primary keys; use
  `gen_random_uuid()`.
- `provider_revision` has no `created_at` / `updated_at`.
- `entity_name`, `entity_description`, `entity_media`, `curated_collection`,
  `curated_membership`, `external_link`, `metric_snapshot` use **bigint** keys;
  `media_asset`, `entity`, `provider_record`, `fact` use **uuid**.
- `uq_active_provider_representation` is a **partial** index (`WHERE is_active`); the
  `ON CONFLICT` target must carry the same predicate.
- `work` has no `id`; its key is `entity_id`.
- DATE parameters must be `date` objects, not strings.


## 2026-11-16 continuation

Worker registration coverage is 11/30. `frontier_tasks.py` now registers the provider
frontier task and preserves the MAL/anime and Bangumi/subject seed rules, leases,
limits and job lifecycle. Frontier walking uses the HTTP clients' shared `ProviderError`
so an actual 404 contributes to the missing-record run. The former local exception
class could not catch errors raised by those clients.

Daily airing refresh now fetches MAL and AniList separately by the target's provider.
It no longer tries a MAL id before fetching an AniList record. A completed daily window
also skips its final target on subsequent invocations.

Validation: lint, format, strict typing and 198 offline tests passed. Tests cover provider
dispatch, completed windows, retry cursor, frontier seed configuration, lease rejection
and registration on the Celery application. The new frontier task has not yet been run
against a real database or broker. Registration coverage is not runtime verification.

The local changes from the earlier `feat/worker-records` checkout are preserved in the
Git stash named `preserve pre-refactor local worker changes 2026-11-16`. Work continues
on `codex/complete-api-migration`, based on `0864f3c` from origin/main.

### Candidate generator continuation

`worker/candidates.py` ports all three title-similarity-v2 legs to async SQLAlchemy,
including multilingual name recall, per-target maximum score, runner-up margin,
structured attributes and hard conflicts. Candidate/evidence writes share a savepoint,
the unique policy key prevents duplicates, and a transaction advisory lock serializes
writers for the same sweep shard. Evaluation messages are published after commit.

Two cursor corrections are intentional: a window fully removed by the decided filter
still advances, and dry runs never reset an exhausted cursor. The next writing run
resets an exhausted pass as before.

`worker/matching_tasks.py` registers the sweep on `sync`. Registration coverage is
12/30, with the floor raised accordingly. This is implementation coverage, not a claim
that all twelve tasks have production verification.

Validation: lint, format, strict typing and 207 offline tests passed. Seven generator
cases cover ranking/margin, the evaluation floor, cursor behavior and year conflicts;
two task cases cover the three-leg allocation, commit-before-publish and registration.
An independent seeded comparison of `_compare` against the legacy function matched
on 1,000 inputs. Real database candidate-set/score comparison remains pending: local
Docker is unavailable and the configured SSH host timed out. Neither production traffic
nor the paused server stack was changed. A broker interruption after candidate commit
still requires the pending-evaluation recovery sweep, which remains to be ported.

### AI matching continuation

`contexts/matching` now owns the preserved entity-match-v2 prompt, a Pydantic v2
proposal model, left/right evidence orientation, run/proposal persistence and conservative
binding policy. Policy creation defaults to shadow mode. Enabled non-shadow policies
still require a passed calibration with enough precision, matching policy version,
confidence/score/margin/evidence thresholds, compatible work families, no hard conflicts
and no conflicting user library entries before calling the resolution engine.

`worker/ai_tasks.py` registers matching evaluation and pending-candidate recovery on
`ai`. Coverage is 14/30, with the floor updated. The recovery query selects pending
candidates with no proposal, including ones committed before a broker publication failed.
The provider client classifies account failures as terminal and transient transport,
429 and 5xx errors as retryable. Account failures set a Redis cooldown when cache is
configured. AI and catalogue HTTP clients now share outbound proxy selection. Pydantic
and Redis are explicit direct dependencies, using the already locked versions.

The candidate row lock spans model evaluation. A separately committed inference run
survives candidate-transaction rollback, and failure status is recorded independently.
This holds a database connection during the bounded model request; concurrency and
real-schema execution still require integration verification.

Validation: lint, formatting, strict typing and 235 offline tests passed. New coverage
exercises output rejection, work-family/conflict gates, shadow behavior, durable failure
ordering, successful run/proposal flow, cooldown/retry classification, pending recovery
and Celery task registration. Queue checking still explicitly reports the migrating AI
queue because classification, evidence extraction and schedule completion are not yet
ported. Real model, PostgreSQL, Redis and broker integration remains unverified.

### Knowledge proposals and local PostgreSQL verification

`contexts/knowledge` now implements work classification and current-observation evidence
extraction with typed Pydantic outputs. Classification checks public visibility and AI
permission across the entire resolved cluster. Extraction checks active representation,
current-observation identity, provider permission and cluster visibility. Policy refusals
persist abstained runs and proposals without a provider call. Model outputs remain
proposals; this workflow does not promote them into canonical facts.

Inference-run creation/failure logging is shared with matching. Input serialization is
bounded at 100,000 bytes; extraction is bounded at 100 validated claims. Tasks are
registered on `ai`, bringing implementation coverage to 16/30. Lint, formatting, strict
typing and 261 offline tests passed. `verify_ingestion.py` was repaired to use the current
session context; its module import now succeeds.

Local integration environment is available again: Docker Desktop was started and a new
isolated PostgreSQL 18 container `codex-migration-pg` created. Its dedicated database
`noshiro_migration_test` was initialized from Django migrations and Alembic through 0004.
This is a test fixture, not production, and is retained for ongoing migration verification.

Executed against that real schema:

- A three-work fixture (one AniList source, two Bangumi targets) produced two candidate
  pairs. The new generator's complete dry-run summary exactly matched the legacy
  generator on the same fixture, including scores, margin and year-conflict count.
- Candidate creation wrote both candidates and their evidence.
- Matching evaluation, classification and extraction persisted succeeded inference runs
  and proposals, using fixed in-process model responses (no external model calls).
- An injected model failure left a failed inference run after candidate rollback.
- A calibrated, enabled test policy applied a bind, wrote an accepted decision and one
  entity redirect through the real resolution engine.

These are bounded fixture checks. Production data parity, the larger recorded baseline,
real broker/Redis/model integration and deployment remain pending. The Tailscale peer is
online; SSH to the existing hostname timed out, while the Tailscale address reached sshd
but rejected the attempted existing-config user authentication.

### Independent database bootstrap

The replacement can now initialize an empty PostgreSQL 18 database through Alembic
alone. `migrations/baseline.sql` is a schema-only capture of the Django migrations,
excluding Django's migration ledger and the four Alembic-owned additions. It contains
no fixture, provider or user data. Revision 0001 replays that DDL for fresh databases;
already stamped installations skip it. An unversioned existing catalogue must be
validated and explicitly stamped rather than silently treated as a fresh database.

The baseline downgrade raises an explicit irreversible-migration error. Later revisions
remain reversible. This avoids giving `downgrade base` a core-table deletion operation.
The baseline still includes compatibility tables used during migration; their retirement
belongs to the final schema cleanup after all callers have moved.

Verified locally on PostgreSQL 18:

- `alembic upgrade head` initialized a new database without executing Django.
- `downgrade 0001_baseline` and `upgrade head` completed on that database.
- `alembic upgrade head --sql` produced executable offline SQL; psql applied it to a
  second empty database.
- The captured schema and restored schema agree except for PostgreSQL's normalization
  of equivalent array casts in the airing-board status constraint.
- Fresh-database ASGI requests to liveness, readiness and catalogue listing returned 200.
- Lint now includes migrations in both the Makefile and CI; scripts are also included
  consistently. Existing 261 tests and strict typing passed.

A PostgreSQL 18 schema job was added to CI to repeat the fresh install and revision
round trip. It has not yet run on GitHub. Production databases were not changed.

### Schedule completion

`contexts/scheduling` replaces the Django schedule-completion service. The configured
Tavily search uses the shared async HTTP/proxy setup; retrieved evidence is retained as
SourceArtifact, AgentStep, AIClaim and ClaimEvidence records. Only curated board entries
are updated. Provider-owned airing facts remain outside this write path.

A confidence-qualified application locks the entry and its board, checks that the board
is still active and the slot still has no start time, and re-reads source references
before appending the claim link. Existing filled slots are preserved; low confidence
and `apply=False` retain proposed claims without changing the slot. Per-entry writes are
atomic, while artifacts and top-level run status survive later failures.

Intentional validation improvements: accepted times must be valid HH:MM values, timezone
names must exist, confidence must be finite and numeric, and supplied durations must be
positive integers. Invalid zones no longer silently compute Tokyo times while storing
a different zone name. Schedule JSON confidence remains numeric, matching the old
payload. The `searched` counter now counts searches; the old implementation left it zero.

The task retains its two-retry and 600/700-second limits. Registration coverage is
17/30. Lint, formatting, strict typing and 282 offline tests passed. Real PostgreSQL 18
fixture runs verified artifact → step → claim → evidence → board application, as well as
filled-slot preservation, low-confidence abstention from application and `apply=False`.
Search and model answers were fixed test responses; real Tavily/model and queue runs
remain pending. No production services or data were changed.

### Conservative proposal application

`contexts/matching/batch.py` replaces the rotating admin/scheduled proposal application
service. It preserves confidence/score thresholds, hard conflicts, compatible work
families, premiere-year tolerance and library conflict protection. Deferred proposals
remain pending for later review; survivor-based cursor advancement and wraparound keep
them from starving the rest of the ring. A transaction advisory lock serializes batch
writers and a savepoint isolates each application failure.

`worker/match_application.py` registers the existing scheduled task with its 3600/3900
limits and `abstain_ineligible=False`. Coverage is 18/30. Common work-family rules now
live in `contexts/identity/work_families.py` and serve both matching gates and resolution.

Two resolution fixes were needed: decisions now use their own savepoint, so a refused
merge cannot leave a candidate marked accepted before the caller records an abstention;
user-library conflicts have a specific exception subtype. Proposal settlement also no
longer writes a nonexistent `ai_proposal.updated_at` column. A concurrent decision is
reported as `already_decided` instead of counting it as a new acceptance.

Validation:

- 288 offline tests passed; the database regression skips unless its dedicated test URL
  is provided. That regression passed separately against PostgreSQL and is wired into
  the schema CI job after fresh migration.
- Complete dry-run batch summaries matched the Django implementation on a shared fixture
  with one eligible and one low-confidence proposal.
- Real application accepted one, deferred one and advanced the cursor to one. A second
  run wrapped and preserved the deferred proposal.
- A real conflicting-library fixture confirmed that a refused bind leaves zero decisions
  and the candidate pending, then the blocked fallback records exactly one abstention.
- Latest-proposal settlement executed successfully against the real schema and was rolled
  back after inspection.

Production execution and the broader data baseline remain unverified.

### Campaign persistence and HTTP controls

`contexts/synchronization` now owns campaign creation, explicit phase transitions,
leases, controls and work-item acknowledgement. The existing staff contract
`POST /api/v1/operations/sync/{campaign_id}/{action}/` is served for pause/resume/cancel.
Creation and resume publish after committing their database state. Retrying an
idempotent creation while still queued republishes the same campaign id, recovering a
previous publication failure without creating a second campaign.

Work-item claims recover expired leases and use row locking. Acknowledgements lock the
campaign before its items and require a running item, matching owner and unexpired
lease. Cancellation revokes running leases. Discovery-page replay uses the existing
(campaign, shard, cursor) unique key. Classified failures preserve terminal 404 handling,
retry timing and attempt limits. Resuming failed items recomputes progress counters from
current item states so retry success cannot count one item twice.

Validation: lint, formatting, strict typing and 295 offline tests passed. Eight opt-in
PostgreSQL tests (seven campaign tests plus the existing matching transaction test)
passed against the independently bootstrapped database. They cover idempotency,
lease ownership/reclaim, stale acknowledgements, retries, resume counters, cancellation,
staff HTTP controls and commit-before-dispatch. The schema CI job now includes both
database test modules; the default offline gate skips them without an explicit test URL.

This is the persistence/control boundary. The complete campaign runner is still pending,
including provider discovery adapters, full related-record imports and campaign AI
normalization/enrichment. The old campaign Celery task is therefore not registered here
and task coverage remains 18/30. General automatic recovery of committed campaigns after
a broker outage also belongs to the pending runner/scheduler. Production was not changed.

### Provider discovery and page checkpoints

The replacement now exposes provider-neutral CatalogPage/DeltaPage values and discovery
adapters for all four sources: VNDB page/id-watermark discovery, AniList catalogue and
air-date windows, frontier-bounded MAL/Bangumi numeric walks, and Bangumi known-record
reconciliation. Bangumi reconciliation starts at offset zero; the old generic campaign
cursor of one skipped its first record. Discovery HTTP clients enforce the stored source
storage policy and close their transports. Exhausted GraphQL rate limits remain
retryable by the campaign instead of becoming an unclassified terminal provider error.

`discover_step` writes each page's work items and next cursor atomically, committing one
checkpoint per page. Already completed discovery does not start over on retry. It
rechecks lease/status and the complete parameter snapshot after provider I/O, so pause,
lease changes or parameter edits cannot be overwritten by a late response. Bounded date
windows and max-pages truncation retain their distinct watermark behavior. Numeric/date
watermarks are not replaced with a generic Unix timestamp.

Lease comparisons and expirations now use PostgreSQL `clock_timestamp()` rather than
transaction-start `now()`. The regression holds a transaction open across an actual
expiry and verifies that the stale worker cannot acknowledge its item.

Validation: lint, format, strict typing and 307 offline tests passed. Fourteen opt-in
PostgreSQL tests passed; database transactions leave the fresh fixture database empty.
New cases cover replay after page completion, pause during provider I/O, stale parameter
snapshots, truncation and window promotion. Four complete serialized AniList/VNDB page
outputs matched the legacy implementations on fixed source fixtures. Provider responses
were mocked; this does not prove live catalogue completeness. The schema CI job includes
all three PostgreSQL test modules.

These adapters and the discovery phase are ready for the pending campaign runner. Full
related-record imports and campaign AI normalization/enrichment remain dependencies, so
the campaign task is still unregistered and migration task coverage remains 18/30.

### VNDB batch transport and embedded source records

The VNDB client now fetches the complete work fields, paginated release/character
payloads, and deduplicated staff details. `include_related=False` performs only the
work request. Official Kana documentation exposed an inherited bug: staff IDs are
`s`-prefixed strings, while the old client accepted only integers. The replacement
accepts canonical IDs and legacy integer inputs, excludes boolean/invalid IDs, and
uses `ismain=1` when retrieving staff details so alias order cannot select the name.
Reference: https://api.vndb.org/kana#post-staff

`ensure_record` atomically creates or refreshes embedded references while preserving
existing payload hashes, revisions and raw-state completeness. Namespace creation now
uses conflict-safe insertion for simultaneous imports of a new resource type.

Validation: lint, format, strict typing and 310 offline tests passed. Fifteen opt-in
PostgreSQL tests passed, including stub-to-full promotion, replay without extra
revisions, URL preservation and refreshing a previously missing full record. Staff
and related-page requests were tested through HTTPX's mock transport. The schema CI
job includes the new record transaction test. Full VNDB graph projection remains in
progress, so its import task remains unregistered and task coverage stays 18/30.

### VNDB work-field projection

Pure source mappings now retain multilingual name kinds/flags, partial-date bounds
and precision, media safety, development status, release roles, and work/release/
character fact values with their JSON pointers. Missing optional fields omit facts;
zero and false values remain meaningful. Character actual-sex/gender facts retain
their spoiler level. Release resolution uses one stable JSON predicate shape.

The async work projection writes the VNDB source revision/observation, exact work
identity, galgame profile, names, description, screenshots/poster safety, external
links, revision-timed metrics, facts, tag mappings and listed collection membership.
It preserves an existing entity audience, clears absent profile fields as the old
VNDB importer did, and keeps the first name flags when duplicate provenance keys
occur. Embedded tags cannot downgrade an existing full source record.

Validation: lint, formatting, strict typing and 320 offline tests passed. Sixteen
PostgreSQL tests passed, covering repeat imports, revision/metric deduplication,
name flags, safety, tag relevance/spoilers, fact provenance, collection reason and
changed-payload profile behavior. A fixed VNDB work fixture ran through the old
Django importer and the async projection in separate rollback transactions. All
eight serialized sections matched: audience, names, media, links, profile, metrics,
tags and facts. The schema CI job includes the new projection transaction test.

This completes the work's own projection. Related releases, characters, contributors,
credits, voices, relationships and cross-provider reconciliation are still required
for the full import entry point. Task registration remains 18/30. Live VNDB calls,
production deployment and final removal of Django are still pending.

### Complete VNDB related graph and task entry point

The VNDB batch importer now projects releases (date precision, official/patch flags,
ratings, work roles, resolution/facts and producer relationships), characters
(appearances, trait groups, spoiler/lie evidence and facts), staff details/aliases,
developer/staff credits, related works and voice performances. Embedded identities
preserve full source payloads. Voices reuse current supported appearances. Batch
projection and explicit-ID reconciliation run in savepoints so an error leaves the
caller's earlier transaction usable and rolls back the complete imported graph.

The official Bangumi-to-VNDB identity policy now creates evidence-backed candidates,
checks work-family compatibility, records bind/abstain decisions, handles refused
merges atomically, and returns the resolved canonical entity. Superseded Bangumi
observations are excluded from reconciliation. Release-work evidence preserves the
original source array index instead of indexing a filtered list; both changes fix
inherited provenance behavior and have targeted regression tests.

The registered `apps.sync.tasks.vndb.import_vndb_work_task` retains the original task
arguments/result. It commits the job claim before provider I/O, checks storage policy,
closes the client, rechecks the live job lease/status under lock before writes, and
commits failure reporting after rolling back failed imports. A job cancelled while
fetching cannot write the catalogue. No related data is fetched when requested, while
embedded credits/relations/voices remain imported from the work payload as before.

Normal-entry database tests exposed two pre-existing replacement job bugs: creation
omitted UUID/non-null defaults formerly supplied by Django, and optional-owner filters
used untyped parameters in `IS NULL`. Job creation now supplies every required default
and owner filters cast the optional value explicitly for asyncpg.

Validation: all lint/format checks, strict typing of 157 modules, and 321 offline tests
passed. Twenty-eight PostgreSQL integration tests passed, including eight graph/identity
cases and four task lifecycle cases. A local Celery eager execution verified the
registered task's argument and request-ID wiring. A complete fixed VNDB graph fixture
ran through the old importer and new importer in rollback transactions. All thirteen
serialized sections matched (credits, releases, release links, ratings, relations,
relationship evidence, appearances, voices, aliases, terms, facts, records and names).
The separate original-array-index test verifies the deliberate evidence-path fix.
The three new PostgreSQL test modules are included in the schema CI job.

Task-name registration is now 19/30. This count is a registration audit, not proof of
full behavior for previously registered tasks; the older AniList/Bangumi/MAL ports
still need their remaining projection paths audited. Campaign orchestration/AI phases,
season pipelines, manual-sync entry points, mail, final app consolidation and production
verification remain pending. Source transport was mocked; no live VNDB graph was fetched
or production data changed in this step.

### MAL metadata and saved-payload parity

Auditing the registered MAL importer found concrete migration gaps. It now accepts
numeric-string episode counts, normalizes timestamp offsets to UTC dates, restores
MyAnimeList link labels/types and the MAL membership reason, returns redirected
canonical identities, and preserves the old profile replacement semantics. Missing
format/count values clear those fields, while unavailable broadcast dates retain the
existing dates. Shared profile writing also supports AniList source-material updates
without changing the defaults existing Bangumi callers use. Collection creation
preserves curated names. VNDB now reuses the same membership writer.

`import_saved_anime` reads the latest active schedule-item revision, checks its identity,
and imports it without network I/O. The full MAL projection uses a savepoint, so a late
failure rolls back records and projections while retaining the caller's earlier work.
Fact evidence now points to real source JSON fields instead of nonexistent predicate-
named paths. Mapper version `mal-anime-v3` records that deliberate mapping correction.

MAL and VNDB single-record tasks now share the tested import coordinator. It commits
claims before provider I/O, applies source storage policy, rechecks the live job under
lock before writes, and commits failure state after rollback. Source adapters validate
IDs and close their clients. Existing task signatures and result types are preserved.

Validation: lint, formatting, strict typing of 158 source modules and 323 offline tests
passed. Thirty-five PostgreSQL tests passed. Seven new MAL database cases cover metadata,
repeat metrics, saved revisions/mismatches, atomic failure, normal task execution,
shared-writer defaults, curated names and returning the canonical identity after a real
merge. A fixed MAL payload matched the old importer across eight serialized sections:
audience, names, media, links, profile, metrics, membership and fact types/values. Evidence
paths were checked separately for the intentional source-pointer correction. The VNDB
thirteen-section legacy comparison still passes after consolidating shared writers.
The schema CI job includes the MAL database test module.

Task-name coverage stays 19/30. This audit completes the bounded MAL metadata import
behavior owned by the old entry point. Remaining AniList/Bangumi projections and the
campaign, season, manual-sync and email flows still need completion before the final
app consolidation and production verification. All source responses used here were
fixed local fixtures. Production was unchanged.

### AniList complete media projection and import entry points

AniList now projects its full media metadata, official/script-aware multilingual names,
source material, partial-date fallback, metrics, genres/tags, related works, characters,
voice actors, staff, studios, episode identities and airing events. Saved season-item
revisions can be imported locally. The task uses the shared leased import coordinator,
storage policy and client cleanup. Batch failures roll back the complete graph.
Shared name and contributor/relation writers now serve AniList and VNDB; existing
VNDB source-specific mappings remain independent.

The full fetch collects subsequent character, staff and airing pages instead of keeping
only the first page. Character/staff limits follow the official Media schema:
https://github.com/AniList/docs/blob/master/docs/reference/object/media.md
Empty nonterminal pages fail explicitly. Embedded references preserve existing entity
metadata, including adult audience. Fallback episode identities include their source
media ID, preventing different works' episode numbers from colliding. Episode links
use the source media ID. Stable episode payloads omit changing countdown values.

The media mapper is now `anilist.media` version `anilist-media-v2`; fact evidence points
to source fields. Re-import retires the earlier partial `anilist.anime` cursor and rebuilds
its selected fields, retaining immutable observations. Revision writing now carries the
upstream update timestamp. The AniList site's own link receives the correct label/type.

Normal-entry auditing also found an incorrect AniList task name/arguments and missing
MAL import-provider support. Create/detail/list requests now support the original three
providers, use each registered task's typed arguments, and commit jobs before publishing.
Broker failure or absent broker configuration durably marks the queued job failed and
returns the original `sync.task_dispatch_failed` 503 response. Frontend import types
now include VNDB/AniList/MAL. Root `make openapi` regenerated the existing snapshot with
no diff; these changes restore the already-declared contract.

Validation: lint, formatting, strict typing of 164 modules and 325 offline tests passed.
Forty-seven PostgreSQL integration tests passed. New cases cover full graph replay,
source metadata, stable episode revisions, next-episode isolation across works,
reference safety, rollback, saved payloads, partial-mapper retirement, task lifecycle,
request dispatch, MAL HTTP create/list/detail and durable 503 failures. Fourteen
serialized AniList graph sections matched the old importer on a fixed payload. The
VNDB thirteen-section and MAL eight-section comparisons still pass. Deliberate link,
source-pointer, reference-safety and fallback-ID corrections have separate assertions.
The schema CI job includes the new database test module. Source transport was mocked.

The frontend gate completed with 234 unit tests, seven browser tests and a production
build. Browser output exposed a React route lazy-loading compatibility error that the
existing page-error assertion missed across reloads; a targeted console regression and
compatibility correction are being verified separately in this goal. Task-name coverage
remains 19/30. Bangumi projection completion, campaign/season/manual-sync/mail flows,
full contract audit, app consolidation and production verification remain pending.

### React route suspension compatibility

The router dependency's lazy component cleared its import promise and stopped calling
React `use()` after the suspended render completed. The installed React version reports
that transition as a recoverable render error. A pnpm-managed patch keeps the fulfilled
thenable stable and calls `use()` consistently, preserving component preload and the
existing missing-module recovery. The patch covers the package source and both module
builds. Dependency versions remain unchanged and configuration stays inside apps/web.

The browser regression now records relevant console errors across navigation/reloads;
checking only the final page's error buffer missed earlier route errors. The focused
workspace test failed against the original package and passed after patching. A resumed
full frontend gate then passed formatting, types, lint, 234 unit tests, dead-code checks,
all seven browser tests and production build using the pinned pnpm 12.14.0. The earlier
parallel timing failures did not recur in this complete run. The API migration goal
continues with the remaining Bangumi and orchestration behavior.

### Bangumi work projection, reviewed terms and identity links

Bangumi work projection now restores original/localized name flags and scripts, reviewed
term aliases, source casing for unmapped tags/infobox keys, anime count replacement,
galgame profiles, rating history and explicit VNDB-ID reconciliation. Shared profile
writing can replace the episode count without clearing another source's format/material.
Provider representations restore the source confidence on replay. Existing galgame
profile details remain intact when the Bangumi projection creates its own work view.

`preferred_terms` reads reviewed global aliases with the original NFKC/lowercase lookup
rules. Mapping uses `bangumi-subject-v2` and real source evidence paths. A projection hash
is included in normalized observation metadata so an alias change produces a new mapping
observation even when the raw revision is unchanged. Previous observations/facts remain
historical, and selection follows the latest mapped output. The raw revision stays intact.

Explicit VNDB IDs are extracted from scoped fields or VNDB URLs with escaped JSON
pointers. Both source arrival orders now use the existing official-ID decision policy.
Cached/embedded subjects can be provided locally and promoted to fetched records while
retaining their entity identity. Complete work imports use savepoints for atomic failure.
The registered refresh entry point now applies source storage policy, performs network
requests off the event loop and closes its HTTP transport.

Validation: all lint/format checks, strict typing of 165 modules and 332 offline tests
passed. Fifty-eight PostgreSQL tests passed. Eleven Bangumi database cases cover metadata,
name flags, rating snapshots, selective profile ownership, galgame details, reviewed and
unreviewed aliases, cached-record promotion, rollback, both identity arrival orders,
refresh policy/cleanup and remapping after an alias changes. Seven standalone cases
cover ID extraction and Unicode alias keys. Eight serialized work-projection sections
matched the legacy subject service on a fixed source fixture. AniList, VNDB and MAL
projection comparisons also passed during this work. The schema CI job now selects all
transaction test modules by their existing naming convention.

The Bangumi character/person/episode and relation workflows are still pending. Calendar
task parity also remains incomplete: the old service always imports base subjects before
building events and optionally runs the full manual-detail sync. The current replacement
still uses its partial existing-identity path. Its docstrings now state that boundary;
earlier calendar projection checks cover only that partial path. Campaign/season/manual
sync/mail completion, final app consolidation, complete contract/runtime auditing and
production verification remain part of the active goal. Source HTTP responses were mocked
and production was unchanged. Task-name registration remains 19/30.

### Complete Bangumi manual subject sync

The manual task entry points now fetch and project work metadata, paginated episodes,
related works, staff credits, character appearances, voice performances and full
character/person records. Shared graph primitives retain source observations and original
collection indices. Episode identities retain the legacy deterministic UUID namespace.
Replays preserve existing entity identities and adult audience metadata. Reviewed role
alias changes create new mapping observations while retaining historical edges.

Each manual sync claims and commits its job before network work, heartbeats while fetching,
closes its transport on failure, and checks live ownership before applying the graph and
success result together. A cancelled or expired job cannot write the fetched catalogue.
Projection errors roll back the complete graph and commit a failed job separately. UUID
entry resolves active Bangumi representations across canonical cluster members. The task
limits are 900/960 seconds, consistent with the other complete provider imports and longer
than the old 300/360-second manual limit to accommodate paginated detail fetching.

Validation: application checks passed with strict typing of 170 modules and 335 offline
tests. All 68 PostgreSQL transaction cases passed. Ten new database cases cover full graph
projection, immutable evidence pointers, subtype/audience preservation, role remapping,
atomic failures, complete task results, policy refusal, provider failure and cancellation.
Three offline cases exercise both Celery entry points and paginated transport requests
with shared staff/voice IDs. Fourteen serialized projection sections match the old complete
manual service on the same fixed source payloads in dedicated rollback-only databases.
No live provider requests or production changes were used for these comparisons.

Registered legacy task names are now 21/30. Calendar completion, campaign/season/mail flows,
full API/frontend/runtime auditing, app consolidation and production verification remain
pending. Calendar still needs mandatory base imports and optional manual detail syncing.

### Calendar orchestration, board continuity and cover storage

The calendar task now imports base subjects before constructing events and can invoke the
complete manual graph sync for each prepared subject. It preserves individual failure
counts and sync-error retry history. Job claims and failure results are committed in
separate scopes, fetching happens outside projection transactions, progress renews leases,
and ownership is checked before catalogue/board writes. Detail fetching keeps the parent
calendar's progress totals. The task transport and cover resources close on every exit.

Calendar refresh now reuses the active board within the same season while preserving
curated metadata/counts and board entries. A season change archives the previous board
with its effective end. Bangumi calendar events are replaced as in the original service.
Refreshes serialize through an advisory transaction lock, including first-board creation.
The projection itself has a savepoint so recording or event failures leave the prior board
intact. Calendar records now use the original canonical URL/schema/mapper versions and
quarter boundaries follow the deployment time zone, defaulting to Asia/Shanghai.

Cover caching retains host/content-type/size checks and the original object paths. The
new storage adapter uses Boto3 1.44.4 and S3-compatible settings, accepting deployed MINIO_*
setting aliases. It retains automatic bucket initialization and tolerates concurrent
creation. Boto3's dependency constraints select python-dateutil 2.9.0.post0. Downloads and
uploads run off the event loop and failed cover uploads remain non-fatal. Static stubs are
app-local development dependencies. No MinIO SDK dependency was added to the new service.

Validation: application gates passed with strict typing of 174 modules and 350 offline
cases. All 74 PostgreSQL transaction cases passed. Six new calendar database cases cover
new-subject import, full detail sync and progress, partial detail failure, policy refusal,
same-season projection preservation, rollover and base failure preserving the old board.
Fourteen storage/cover cases check request shape, public URLs, missing/concurrent buckets,
settings aliases, invalid object paths, content/size limits and non-fatal upload errors.
The calendar Celery entry also has an argument/owner regression. Sixteen serialized graph
and calendar sections match the old services on fixed source data. Storage calls were
validated with botocore request stubs and image HTTP with mock transports. Live S3/MinIO,
live source requests and production deployment remain unverified in this step.

The nine unregistered tasks, campaign/season orchestration, full endpoint/runtime auditing,
app consolidation and old-system removal remain pending. Registration coverage stays
21/30 and represents task names, with behavior verification tracked separately above.

### Queued verification mail and account-code parity

The verification task is registered on the replacement realtime worker. It reads the
stored verification and skips missing, used or expired rows before delivery. Provider
failures retain bounded Celery backoff/retries. The HTML template and sender branding now
match the original mail builder, including escaping dynamic values and the five-minute
expiry text. The template is a packaged resource with no dependency on the old source.

The request route now commits a five-minute code before publishing through the shared task
dispatcher. A case-insensitive email/purpose scope lock and 60-second send interval restore
the original send behavior. Verification locks the chosen row and checks expiry and the
five-attempt limit. Incorrect attempts remain committed. The previous replacement accepted
expired codes and created ten-minute codes without enforcing the send interval. A broker
failure now returns 503/users.email_delivery_unavailable after the code is committed.
Duplicate registration/social router inclusions were also removed from the app factory.

The default replacement worker now consumes ai in addition to realtime/sync. All legacy
AI task names have implementations, so the old queue-check exemption no longer applies.
The check fails if any routed queue lacks a default consumer. The deployment configuration
still contains the legacy services pending final consolidation and has not been applied.

Validation: the new service passed lint, format, strict typing of 176 modules and 353
offline cases. All 81 PostgreSQL transaction cases passed. Seven new database cases exercise
the HTTP entry, case/purpose throttling, both broker-failure paths, expiry, attempts/used
codes and retryable delivery. Offline regressions cover HTML escaping, the actual Celery
entry and unique method/path registration. Sixteen text/HTML comparisons against the old
builders matched across purposes and escaped values. The built wheel includes the template,
and the real worker application registers 22 migrated task names. Queue checks pass for
ai/realtime/sync. Root make openapi completed without snapshot changes. Mail HTTP was mocked
and no email was sent. Production verification remains pending, with the latest SSH attempt
to the server's Tailscale address rejected by publickey/password authentication.

Eight task names remain unregistered. Campaign/incremental/season orchestration, complete
HTTP contract and runtime auditing, professional module layering, final app consolidation
and old service/code/dependency/schema removal remain in scope. The verification expiry
and interval gaps are additional evidence that prior HTTP shadow comparisons alone do not
prove complete behavior parity. The active goal remains unfinished.

### Campaign prerequisite — evidence-backed vocabulary normalization

The knowledge context now contains typed normalization input/output contracts, language
selection, reviewed vocabulary/namespace/language aliases, model fallback and source-backed
claims. Missing stable term slugs change map_existing into propose_new as in the old skill.
Model failures preserve the raw vocabulary and retain a failed inference/step audit. The
normalizer records proposals without changing taxonomy terms or canonical entity fields.

Durable agent-step allocation locks the run before selecting the next sequence. Shared
inference creation accepts an optional agent-step link without changing existing callers.
Observation evidence must still be an active representation of the target, and artifact
references are checked against their owning run when applicable. Evidence is validated
before inference and again before claim creation. A source revoked during inference leaves
a failed completed step and no claim. This avoids leaving a running step behind after a
claim transaction rolls back. Standalone normalization retains the old no-agent behavior.

Validation: application checks passed with strict typing of 178 modules and 353 offline
cases. All 90 PostgreSQL transaction cases passed. Nine new database cases exercise model
and reviewed-alias paths, immutable source links, invalid model fallback, unstable slug
handling, inactive/revoked sources, standalone calls and artifact evidence. Four serialized
sections for steps, inferences, claims and evidence match the legacy skill for model and
alias results on fixed inputs. Model responses were mocked, with no external inference or
production changes.

This is a prerequisite module for the campaign normalizing phase. The campaign runner is
still unregistered, and the enrichment skill and orchestration integration remain pending.
Task registration stays 22/30. Full HTTP/runtime auditing, app consolidation, removal of
old services/code/dependencies/schema and production verification remain required.

### Campaign prerequisite — cached web evidence for enrichment

The knowledge context now captures individual search results as immutable, content-hashed
artifacts linked to durable tool steps and invocations. Identical recent searches reuse
the configured cache across agent runs. Search failures return an empty evidence set while
retaining failed step/invocation audit. Artifact persistence and successful tool completion
share a transaction, so a later artifact error rolls back partial capture.

The shared agent-step writer now supports tool steps and nullable failed-step output.
Search invocation keys include their allocated step ID. This retains separate attempt
history and permits a failed or empty search to be retried for the same entity/run without
colliding with the original invocation's unique idempotency key. Cache keys still depend on
the original query parameters and tool version. Artifact claims may later reference cached
search evidence from a prior run, matching the enrichment service's existing cache behavior.

Validation: application gates passed with strict typing of 179 modules and 353 offline
cases. All 97 PostgreSQL transaction cases passed. Seven new database cases verify cache
hits, cross-run reuse, expiry, blank queries, failed/empty retries and atomic rollback after
partial artifact capture. Three serialized sections for steps, tool invocations and
artifacts match the old enrichment search/cache flow on fixed inputs. Invocation attempt
keys are intentionally different as described above. Web search was mocked and no provider
quota was consumed. A Tailscale SSH attempt also failed host-key verification, so production
access remains unresolved and no remote changes were made.

The enrichment proposal/application skill and campaign runner integration remain pending.
These new prerequisite modules do not change the 22/30 registered task count. Final app
consolidation, legacy code/service/dependency/schema removal and end-to-end verification
remain part of the active goal.

### Campaign prerequisite — multilingual enrichment proposals and title application

The knowledge context now completes missing multilingual fields using the restored web
evidence cache and typed model contracts. One schema retry is retained. Each attempt links
its inference audit to the durable skill step, and accepted proposals record calibrated
confidence and source observation/artifact evidence. Shared claim/evidence and inference
completion writers are reused by vocabulary normalization and enrichment.

Enrichment defaults to reviewable proposals. Explicit application can add high-confidence
titles with source provenance and machine-generated flags. Descriptions remain proposals.
Logical duplicate names are superseded across provenance records, including pre-existing
multiple-source copies. Entity locking serializes title checks and inserts. Oversized title
or script values remain full reviewable claims because they cannot fit the name columns.
The complete proposal/application pass is atomic. Source revocation or a later write failure
leaves no partial names/claims and completes the step with failed audit. Failed model
contracts retain a failed step instead of being overwritten by a successful abstention.

Validation after resuming: all application gates passed with strict typing of 181 modules,
353 offline cases and 109 PostgreSQL transaction cases. Twelve new enrichment database
cases cover default review mode, calibrated title application, description handling,
provenance/duplicate behavior, web evidence, schema retries, failed contracts, oversized
values, filtering, source revocation, partial-write rollback and missing targets. Six
serialized sections match the old enrichment service for review/application/replay using
fixed model responses. Fresh entity UUIDs and timestamps are excluded from those stable
projection comparisons. The existing normalization comparison still matches. No model or
search-provider calls were made.

The enrichment module is now available for campaign integration. The campaign runner and
its other unregistered tasks remain pending, with registration still 22/30. Full application
consolidation, legacy removal, remaining behavior audits and production verification are
still required before the goal can complete.

### Resumable campaign runtime and production access

Registered the durable campaign runner across discovery, fetching, normalization,
enrichment, reconciliation and review. Source projection and work acknowledgement commit
atomically. Campaign and item ownership gates reject expired, cancelled or replaced leases.
A pause permits the in-flight unit to finish and then stops progression. Discovery cursors,
source-backed AI checkpoints, retry deadlines and bounded continuation survive subsequent
worker invocations. Required AI mode rejects raw fallback. Review, agent-run completion and
incremental watermark promotion share the terminal transaction.

Continuation publishing has bounded broker-error retries and records a recoverable failed
campaign when the unleased continuation cannot be sent. API dispatch errors return the
existing service-unavailable envelope after retaining the queued campaign for retry.
Full missing-record reconciliation requires an authoritative, complete enumeration and
preserves records observed after the campaign started.

Production scale inspection exposed the cost of counting the entire queue after every
acknowledgement. Terminal deltas now update counters exactly once under the item lock.
Discovery adds inserted-item counts, and recovery/final review recompute aggregates.
Migration 0005 supplies ordered partial indexes for queued, normalization and enrichment
work. Its index-path fixture establishes usable access paths with planner settings, while
production-copy performance verification remains pending. Steps default to a 240-second
budget and 1200-second leases. The existing phase and item limits remain configurable.

Validation passed with 359 offline cases, 138 PostgreSQL transaction cases and strict typing
of 184 modules. Eight serialized complete assisted-campaign sections match the old service
with fixed provider/model responses. Task registration is now 23/30. Remaining tasks cover
incremental synchronization, season pipelines/rollover and provider-link recall. Full HTTP,
MCP, deployment and layering audits, app consolidation and legacy removal remain required.

SSH access was restored using the user's supplied login. Production services were stopped
and deployed source trees contained local changes. Started the existing PostgreSQL container
to inspect revision 0004 and capture a full backup. Other application services remain stopped.
The database is approximately 37 GB with 845676 works, 3704656 provider records and 14 users.
Private source patches, heads, environment and role backups are outside Git on the PSSD.
The object-storage archive passed listing/checksum validation. The database archive is still
being captured as of this entry. No production application/schema changes have been applied.
A complete isolated restore and migration rehearsal must follow archive completion.

### VNDB daily incremental launcher

Restored the scheduled daily VNDB campaign launcher using the existing campaign creator,
committed job leases and explicit sync-queue dispatch. A daily idempotency key reuses the
same campaign. Publishing occurs after the campaign commits. Broker failure retains that
campaign and durably fails the launcher job so an operator can retry the same daily sweep.
Completed jobs reject duplicate delivery. The local process date remains the daily-key
boundary, matching the previous launcher.

Validation passed with 359 offline cases, 140 PostgreSQL transaction cases and strict typing
of 184 modules. Two database cases cover daily replay, job replay and failed dispatch
recovery. Registration is now 24/30. Season pipelines/rollover, Bangumi incremental sync and
two link-recall tasks remain required, along with the broader unfinished migration work.

### Seasonal snapshots, board projection and quarter rollover

Registered the MAL season pipeline, multi-source season pipeline and rollover task. Source
capture retains pagination, AniList's release-status/horizon filtering, per-item saved
payloads, MAL broadcast normalization and current-snapshot compaction. Each source finishes
network retrieval before the snapshot/items transaction. A failed fetch or later item write
leaves no partial snapshot. Retention preserves referenced observations, including JSON
source references on curated board entries, and restricts deletion to MAL/AniList season
namespaces. Its foreign-key inventory is checked against the schema.

Restored saved-media promotion and candidate generation with isolated source legs. Weekly
projection preserves the prior provider-priority, corroboration, format, premiere and
weekday-less film/OVA/special rules. Entries and board metadata are replaced atomically
under the existing calendar advisory lock. The daily refresh can rebuild a previously empty
board before selecting targets. Candidate evaluation dispatch follows committed persistence.

Rollover fixes two defects in the old orchestration. During the grace period Bangumi
prefetch now captures an observation without switching the active board. After the switch,
the result checks the current active board instead of reloading the archived board object.
This permits the expected successful-switch result and retirement of stale daily shards.

Validation passed with strict typing of 189 modules, 369 offline cases and 158 PostgreSQL
transaction cases. The complete seasonal records, observations and board-entry comparison
matches three old serialized sections after accounting for already-established mapper
version increments and the prior AniList episode canonical-URL correction. Fixed source
responses were used. Registration is now 27/30, with Bangumi incremental synchronization
and two link-recall tasks still pending. App consolidation and legacy removal remain open.

The full production archive completed and passed archive/checksum verification. It restored
successfully into the isolated local noshiro_production_rehearsal database. Upgrade from
0004 to 0005 succeeded and all three indexes are valid. The five entity-kind counts, 14
users and 3704656 provider records match the production baseline. The first public HTTP
shadow pass matched 171/171 comparisons across 20 sampled entities and 11 list endpoints.
The expanded pass also matched 491/491 comparisons across 60 sampled entities and the same list paths. Indexed queue-stage queries on the three largest campaigns
(66231, 65500 and 21988 items) completed below 1 ms on this local restored copy. These local
measurements do not establish production hardware performance. Detailed private backup,
restore, baseline and query-plan reports remain outside Git. Production application/schema
changes have not been applied, and only the existing production PostgreSQL service was
started during backup preparation.

### Restored-copy authenticated HTTP audit and notification parity

The expanded public shadow pass matched 491/491 comparisons. A local-only token for an
active user on the restored copy exercised twelve authenticated paths in addition to the
list paths. It exposed notification filtering differences that the empty fixture missed.
The default query now retains the old unread-only behavior, explicit true selects read
rows, and explicit empty input selects both states. Accepted boolean spellings and invalid
input retain the existing validation envelope.

Notification list and read-state responses now batch-load all five target types, with
nested activity/comment references and content owners. The loader deduplicates targets,
handles missing references and bounds cycles through the visited reference path. Existing
pure payload helpers remain compatible. The read-state transaction still updates once.

Validation passed with strict typing of 190 modules, 380 offline cases and 159 PostgreSQL
transaction cases. The restored-copy HTTP run now matches 23/23 list/authenticated paths
and eight explicit filter variants. Tokens and detailed logs remain local/private.
Notification cursor tie offsets/reverse paging, along with the broader cursor endpoints,
still require the final pagination audit. These checks do not complete the whole migration.

### Bangumi incremental synchronization

Registered the incremental task with the eight existing task configurations and their
subject, episode, relation, character and person handlers. Existing active provider IDs
initialize cursors, with completed full-sync state as the fallback. Defaults remain 1000
items, 20 consecutive errors and 50 consecutive skips. Provider 404s and missing required
subjects remain skipped outcomes. The missing-ID frontier retains the last live ID.

A committed running state reserves each window. Its update timestamp is an optimistic
ownership version. Every canonical import and cursor/job acknowledgement commits in the
same short transaction, with version/ownership checks before projection. Replacement of
that state during source retrieval rejects the late write. Failures preserve the error
ledger and last successful cursor. The stale-state scanner now rechecks its cutoff in the
conditional update so it cannot unlock a state that made progress after selection.

Bangumi relation projection accepts omitted collections. Incremental staff/character/work
relation imports therefore reuse the complete graph writers while preserving the other
collection observations. Existing complete-subject callers still provide all collections.
The 14-section complete Bangumi graph comparison continues to match the old implementation.

Validation passed with strict typing of 192 modules, 380 offline cases and 174 PostgreSQL
transaction cases. Fifteen incremental database cases cover all handler families, cursor
continuation/legacy initialization, job replay/totals, frontier skips, failure durability,
state replacement, partial collection isolation and stale-scanner races. No source requests
were made. Registration is now 28/30. The two AI link-recall tasks, complete pagination/HTTP
and MCP audits, app consolidation, legacy removal and production deployment remain pending.

### MAL-anchored Bangumi search linking

Registered the MAL-to-Bangumi search linker with the existing task name and batch defaults.
Three multilingual search queries cover distinct scripts. The model receives compact,
deduplicated search hits and may select only a returned ID at confidence 0.92 or higher.
The default creates a reviewable candidate with provider-search evidence. Explicit application
uses the existing resolution engine and records refused binds as abstentions. Subject import
commits before the optional episode refresh, retaining the old partial-refresh behavior.

Search, model inference and candidate writes have durable audit. Search artifacts now link
through a tool invocation and step to their agent run. Selected-result snapshots retain the
existing internal artifact representation. A shared content-addressed artifact writer also
serves enrichment search, whose three-section cache/evidence comparison still matches.
The model and step writers reuse the shared inference/agent-run services.

Attempt acquisition is serialized by idempotency key. The running row's update version gates
late model, source and candidate writes. Paused/waiting attempts report their current state.
Interrupted running attempts become reclaimable after the existing 3900-second hard-task
window, configurable with BANGUMI_LINK_ATTEMPT_STALE_SECONDS. Recovery fails unfinished
step/inference/tool audit before beginning the next attempt. Restored production data contains
five running Bangumi-link attempts, making this recovery path relevant to deployment.

Validation passed with strict typing of 198 modules, 388 offline cases and 194 PostgreSQL
transaction cases. Sixteen link database cases cover pending/application behavior, evidence
rollback, replay/force, actionable walk budgets, missing/low-confidence IDs, outages,
interrupted ownership, model contracts and stale recovery. Four provider-search database
cases cover scope enforcement, unavailable retries, owned artifacts and cancellation during
retrieval. Five serialized candidate/evidence/run/inference/representation sections match
the old linker after excluding generated IDs. The added tool-invocation trace is checked
separately. Source/model responses were mocked throughout validation.

Task registration is now 29/30. MAL agent-based recall and its native tool-calling transcript
runtime remain required. Complete pagination/HTTP/MCP audits, professional layering and
configuration cleanup, app consolidation, legacy service/code/dependency/schema removal,
production cutover and post-deployment verification remain part of the active goal.

### Durable native tool-calling runtime

Added native OpenAI-compatible tool calls, typed knowledge/MAL retrieval tools, ordered
transcripts, persisted budgets and terminal checkpoints for the remaining MAL recall
workflow. Model selection preserves the configured fast/reasoning tiers, timeout and JSON
output cap. Usage records include provider token counts and configured per-model costs.
Transient model failures retry within the run's execution budget. Each model attempt and
tool execution consumes a step, including failures, so repeated retrieval failures remain
bounded.

Run ownership gates transcript and canonical writes. A response received during a pause
retains its inference audit and charges usage once. Resume reuses that response, completed
tools and committed final answers. Recovery also completes a parent model step interrupted
after its last tool reply was committed. Final output, step completion, run status and
checkpoint commit together. Tool evidence uses the existing content-addressed artifacts,
scope checks and provider storage policy. Public knowledge tools share catalogue/detail
projections. Catalogue callers retain the existing count behavior while tool searches can
skip the count query.

Validation passed with strict typing of 203 modules, 395 offline cases and 210 PostgreSQL
transaction cases. Eleven native-loop database cases cover tool turns, retries, validation,
budget enforcement, pause/in-flight responses and crash recovery. Transcript/checkpoint
tests cover hashes, ordering and rollback. Retrieval tests cover public/private visibility,
compact MAL fields, storage policy and client cleanup. All source/model responses are
mocked. Shared Bangumi linker/search tests continue to pass. The new runtime has not yet
been connected to MAL recall, and task registration remains 29/30. Consolidation, cleanup,
complete contract audits and production deployment remain pending under the active goal.

### MAL agent recall and complete task registration

Registered the final MAL recall task on the sync queue with its existing batch setting and
3600/3900-second execution limits. The active-board sweep resolves canonical anime roots,
deduplicates entries, skips pending MAL candidates and walks past concluded or controlled
attempts without consuming the actionable limit. Failed/cancelled attempts retain their
audit when a new attempt acquires their released idempotency key. Stale running attempts
resume in place. Paused/waiting attempts preserve their control state, including force runs.

The retrieval loop uses the existing multilingual/season-aware prompt and three typed tools.
A found ID must occur in a MAL search result or an explicit MAL anime source returned by
the entity-detail tool. High-confidence candidates remain pending with agent_mal_recall
evidence. Existing MAL identities are reused. Source import, candidate/evidence creation and
materialization acknowledgement commit atomically under an owned projection lease.
Materialization errors retain the successful model decision for retry without another
inference request. Interrupted projection ownership prevents late imports. Evaluation
publication happens after commit. The existing pending-candidate evaluation sweep provides
retry after a broker outage.

Native recovery now also recognizes a completed legacy final step from its matching
transcript/inference output, retaining the already-saved legacy budget. Recovery closes
queued legacy steps and unfinished child audit before replaying incomplete work.

Five serialized candidate, evidence, representation, inference and transcript sections match
the old recall implementation in rollback-only fixtures. Intentional additions include the
observed-ID check, durable post-model materialization retry and execution-attempt accounting.
Validation passed with strict typing of 206 modules and 631 cases with PostgreSQL enabled
(402 offline and 229 transaction cases). Seventeen recall database cases and seven offline
cases cover the task contract, skips, confidence, unsupported IDs, source/evidence rollback,
retry, stale/controlled attempts, force and broker failure. Two additional native recovery
cases cover legacy final steps and queued audit. Source/model responses were mocked.

Static task coverage is 30/30 with no missing or unknown names. This establishes registration
coverage. Full HTTP pagination/mutation/validation and MCP audits, professional layering and
configuration cleanup, consolidation into apps/api, legacy service/code/dependency/schema
removal, production cutover and post-deployment verification remain required.

### Cursor pagination contract audit

Replaced the incomplete forward-only cursor boundaries on activity timelines, notifications
and import-job history. Equal timestamp groups retain their offset, reverse cursors reverse
both the comparison and SQL ordering, and both navigation links preserve the legacy token
format. Shared link rendering retains repeated/blank filters and the old query-key ordering.
Offsets above the existing 1000-row cutoff clamp to that cutoff. Timestamp positions bind
as datetime values, fixing the asyncpg error caused by binding their string representation.
Invalid timestamp positions return the existing 404 invalid-cursor response.

A pure comparison covers 5000 legacy cursor states, including timestamp ties, direction
changes and empty pages. All page windows and both encoded boundaries match. A read-only
HTTP comparison on the restored production copy matches 60 complete old/new responses,
including both links and reverse navigation across the six cursor endpoints. Six HTTP
database cases traverse tied timestamp groups forward and back through public, personal,
user and feed activity, notifications and import history. Permanent unit cases cover
offsets, empty pages, timestamp binding and link query preservation.

Validation passed with strict typing of 206 modules, 409 offline cases and 235 PostgreSQL
transaction cases. The wider page-number/validation/mutation contract audit remains pending,
along with MCP, context/configuration cleanup, app consolidation, legacy removal and
production deployment. The local replacement HTTP server was restarted against the restored
copy for these comparisons. Production application services remain stopped.

### Page-number pagination and size validation

Restored last-page selection across the page-number read models using their filtered count.
Invalid/zero/negative page numbers return the existing 404 response. Page sizes retain the
legacy fallback for blank, zero, negative and malformed values, including cursor endpoints
where FastAPI previously rejected them before pagination ran. A Pydantic before-validator
keeps page-size parameters typed as bounded integers in the generated contract. Last-page
resolution and range checks happen before SQL offsets, including arbitrarily large page
numbers. Count-free catalogue tool searches retain their existing numeric window behavior.

Page links preserve original page-size/filter spellings, repeated and blank query values,
and query-key order. Previous links to the first page remove the page parameter, matching
the existing contract. A pure comparison matches 1232 legacy requests across empty/nonempty
collections, both endpoint defaults, last/invalid pages and size variants. Status codes,
selected windows and complete links match. A separate read-only comparison on the production
copy matches 88 HTTP responses across seven page-number paths and three cursor paths.

Permanent HTTP database tests cover final-window selection and backward navigation for
catalogue/tag listings, invalid page values beyond PostgreSQL integer bounds, and malformed
page-size fallback on all six cursor endpoints. Validation passed with strict typing of 206
modules, 421 offline cases and 237 PostgreSQL transaction cases. General request validation,
mutations and MCP remain pending. The MCP service still exists only in the legacy app and
must be migrated before app consolidation and production deployment.

### Internal MCP data and tool migration

Added the existing MCP 2.3 dependency to the replacement toolchain and introduced an
async internal server factory with the three existing tool names. Public projection
queries reuse the migrated catalogue/detail readers. Relation queries retain the
100-source-row cap, canonical target deduplication and public visibility checks.
Candidate reads preserve safe summaries and matching evidence fields.

Client-submitted proposals validate through the existing matching output model. The
candidate lock, successful internal_mcp inference audit and pending proposal commit
in one transaction. The internal tool retains its structured acknowledgement and
read/write annotations. Three database cases exercise real SDK tool dispatch, audit
fields, pending status, missing candidates and rollback after a proposal insert failure.

Validation passed with strict typing of 210 modules, 421 offline cases and 240 PostgreSQL
transaction cases. The public authenticated HTTP server, rate limiter, stdio/HTTP transport
tests and full legacy MCP comparisons remain pending. This checkpoint completes the
internal data/tool path, while the full migration goal remains active.

### Public MCP transport and authentication

Added the stateless JSON Streamable HTTP entry point with the existing three public
tool names and read-only annotations. The SDK authentication, auth-context and scope
middleware surround the transport while allowing its lifespan to run. Existing access
tokens retain the legacy MCP signature/expiry/access-type/active-user checks. Malformed
user identifiers reject before database binding. Refresh tokens and inactive users reject.

Per-subject fixed-window limits use atomic Redis increment/expiry when a Redis cache URL
is configured. Both the existing CACHE_URL and REDIS_CACHE_URL are accepted, with bounded
connection/read timeouts. Local runs retain process-local limits with expired-window cleanup.
Tests exercise HTTP middleware and real SDK dispatch through ASGI, including missing/invalid
tokens, authenticated discovery, structured tool results and rate refusal. A separate SDK
client launches the internal stdio process, initializes it, discovers all three tools and
checks argument errors. PostgreSQL verifies JWT user lookup and disabled-user rejection.

Full legacy query/proposal parity, a live Redis limit exercise and production transport
configuration remain required before MCP cutover. Broader validation/mutation audits,
consolidation, legacy removal and deployment remain pending under the active goal.

Validation passed with strict typing of 212 modules, 425 offline cases and 241 PostgreSQL
transaction cases. Public HTTP tests run through the SDK transport lifespan and middleware.
JWT database tests cover active/inactive users, refresh/expired tokens and malformed user
identifiers. An unconfigured signing secret rejects authentication. The stdio case starts
the internal server as a separate process and exercises initialization, tool discovery and
argument validation through the SDK client. Redis-backed limits still require a live Redis
verification before deployment.

### MCP query parity and live Redis verification

Compared six legacy query/submission sections against rollback-only equivalent fixtures.
The comparison exposed three raw MCP detail fields omitted from the HTTP-oriented detail
reader. Public MCP now includes listed memberships, merged-source identifiers and the merge
flag while preserving the existing HTTP serializer shape. Search, entity detail, relations,
candidate evidence, inference audit and proposal records match the old implementation.
Permanent database coverage checks listed memberships and private relation targets.

A dedicated Redis 8 instance verifies the actual Lua increment/expiry path. Forty concurrent
requests across two limiter instances allow exactly three and refuse thirty-seven at a limit
of three. The shared counter reaches forty and has a positive bounded expiry. Unique test
keys are removed after verification. The opt-in test uses NOSHIRO_INTEGRATION_REDIS_URL.

Validation passed with strict typing of 212 modules and 668 cases with PostgreSQL and Redis
enabled. The temporary Redis container is removed after the exercise. Production MCP transport
configuration, general request/mutation validation, context/configuration cleanup, app
consolidation, legacy removal and deployment remain pending under the active goal.

### Periodic scheduling and worker transport configuration

Loaded all 18 existing beat entries into the replacement Celery application. Calendar,
incremental and matching-sweep cron environment settings use validated application settings.
The serialized task names and all five expanded cron fields match the old schedule table.
Maintenance tasks route to realtime before the broader synchronization route, including the
shared publisher. All three queue exchanges/routing keys are declared explicitly.

The worker retains the existing 7200-second broker visibility timeout and environment override,
JSON content/serialization settings, 20/30-second default execution limits and retry delay.
Per-task long-running limits continue to override the defaults. Scheduler tests load the full
table and publish representative maintenance, sync and AI entries through Celery's in-memory
broker, then consume each message from its intended queue. Cron override coverage verifies the
existing environment names. Production beat startup still requires the deployment cutover.

Validation passed with strict typing of 213 modules, 429 offline cases and 242 PostgreSQL
transaction cases. The dedicated Redis case is skipped in this run because its temporary
instance was already removed after the preceding live verification. The active goal continues
with local app consolidation, retained-work reconciliation and deployment/runtime cleanup.

### Local application consolidation

Moved the async application into apps/api and removed the Django source, dependency
lockfile, management commands, migrations, framework tests and old service compose files
from the active checkout. The complete former app, including local environment files,
is retained outside the repository under the private migration backup directory.
The user's pre-refactor stash remains intact. Its NullPool worker-session behavior,
CI registration/queue gates and worker deployment intent are represented in the current
implementation. Migration-only handoff documents were removed and this ledger now lives
under docs alongside the architecture conventions.

Root commands and the retained API workflow now target the unified app. OpenAPI exports
from the actual FastAPI application into the existing snapshot location. Frontend page
query types accept last-page requests, including the two locally paginated projections.
The task-name inventory retains the existing broker protocol without importing old code.
The production manifest uses one application image for HTTP, three workers, beat and MCP.
Worker health probes use the new runtime and beat checks its expiring Redis heartbeat.
Compose interpolation validates using dummy credentials and an empty environment file.
No production services were started or changed by this local consolidation.

Validation from the unified directory passed strict typing of 214 modules and 674
PostgreSQL-enabled backend cases, with the dedicated Redis case skipped after its earlier
live verification. Web checks passed 234 unit and seven browser cases plus build, lint,
formatting, types and dead-code checks. Production rollout, remaining request/mutation
validation and old database/support-service cleanup remain pending under the active goal.

### Access-token and stored-password error handling

Shared access-claim validation now serves HTTP and MCP. Required access claims, token
expiry, signing-key presence and PostgreSQL-compatible positive user identifiers are
validated before user lookup. Malformed subjects and oversized integers produce the
existing 401 token_not_valid response. Optional authentication retains anonymous fallback.
The active-user and password-revocation checks remain in the HTTP dependency.

Invalid PBKDF2 iteration counts reject cleanly, and non-ASCII stored digests compare as
bytes without raising. The password format and valid stored-hash behavior are preserved.
Regression coverage includes malformed claims, missing signing configuration, required
claims, valid access/password changes and a real HTTP problem response before database
binding. Stored-hash regression cases cover invalid rounds and digest text. General query,
body and mutation validation remain part of the active migration goal.

Logout uses the same claim parser with the refresh-token type. Missing/malformed refresh
claims retain the existing cookie-clearing 204 behavior. A key-share lock on an existing
user prevents deletion racing the outstanding-token insert. Tokens for deleted users skip
blacklisting and still end the session. PostgreSQL cases verify malformed subjects,
idempotent blacklist writes and missing-account logout through the normal HTTP endpoint.

Session issuance rejects an absent signing key with a structured 503 authentication
configuration response. This prevents a successful login response containing an unusable
empty-key token. Valid configured token issuance remains unchanged.

Validation passed with strict typing of 214 modules, 455 offline cases and 246
PostgreSQL transaction cases. The dedicated Redis case remains skipped in this run.
Production rollout and the remaining general request/mutation contract work are pending.

### Framework validation and container runtime

FastAPI request validation now returns the existing structured 400 problem response,
including field errors. Malformed path identifiers return a 404 problem. Missing
routes, unsupported methods and malformed JSON use the same response envelope.
OpenAPI describes the actual 400 and path-related 404 responses. The frontend
regression case verifies field errors and trace identifiers through its API client.

The complete quality gate passed 708 backend cases, with one optional Redis case
skipped, strict typing of 215 modules, 235 web unit cases and seven browser cases.
The locally built ARM64 container runs as UID 10001, has no Django package, loads
all 18 periodic schedules and returns successful liveness, readiness and collection
responses against the restored production database. Its OpenAPI matches the checked-in
snapshot. The base image came from the public ECR Docker library mirror after the
Docker Hub authentication request timed out. The Dockerfile now accepts a base-image
override while retaining its existing default. Production needs an AMD64 build.

SSH access to the production host has been verified. PostgreSQL is healthy and the
application containers remain stopped. Production rollout and remaining mutation,
schema-retirement and deployment cleanup work continue under the active goal.

### Browser session deployment settings

Production configuration inspection found that refresh-cookie options and CORS
were absent from the replacement service. Shared cookie helpers now apply the
configured name, path, domain, secure flag, SameSite and cookie lifetime across
password/code/social login, registration and logout. Existing JWT_REFRESH_COOKIE
variables remain readable during environment migration. JWT_SECRET is the canonical
signing setting, with the existing key accepted as a fallback to preserve sessions.
The example environment uses current names and MCP defaults to its dedicated port.

HTTP CORS middleware now reads the production origin and credential settings.
Origin lists accept existing comma-separated values and JSON lists. Browser tests
cover credentialed authorization preflight, allowed-origin error responses, rejected
origins and the development allow-all setting. Cookie tests verify environment
parsing, signing-key precedence, matching issuance/removal scope and HTTP login/logout.

API validation passed strict typing of 216 modules and 718 PostgreSQL-enabled cases,
with the dedicated Redis case skipped. One stale-state timestamp case failed in an
initial full run, then passed in isolation and in both subsequent full runs. No
behavior change was made to that scanner. Production containers remain stopped.
The frontend's refresh endpoint was found missing during this audit and is the next
required session change before rollout.

### Refresh-token endpoint and route inventory audit

Registered the browser's existing sessions/refresh endpoint. Rotation locks the
account before checking revocation, validates active-account and password state,
blacklists the consumed token and records its replacement in one transaction.
Custom token claims survive rotation. Pre-fingerprint refresh tokens acquire the
current password fingerprint. Logout shares the context-owned revocation service.
Stored token identifiers and expiry values are validated before database binding.

PostgreSQL regression cases cover replay, logout revocation, inactive/deleted users,
password changes, legacy claims, malformed claims and a replacement-insert failure.
Two simultaneous HTTP requests through independent PostgreSQL connections produce
one successful rotation and one rejection. A failed replacement insert rolls back
the consumed-token revocation. The web client already calls this endpoint with the
matching payload, so its existing contract requires no change. OpenAPI was regenerated.
Root checks passed 731 backend cases and 235 web unit cases, seven browser cases,
strict typing of 218 modules and the remaining lint/build checks. Redis remains an
explicit opt-in case skipped in this run.

A fresh inventory from the retained Django URL resolver identified further missing
HTTP operations. Avatar upload, episode progress, own/public reviews, public library
and collection detail/items, generic comment list/create and mute actions need porting.
The versioned OpenAPI URL also needs preserving. Existing tests and sampled payload
comparisons did not cover this complete route inventory. These gaps keep production
cutover and old runtime/database retirement pending under the active goal.

### HTTP operation inventory and mute actions

Retained a 93-path, 127-operation public HTTP inventory independently of the old
runtime. Run `uv run python scripts/route_coverage.py` from apps/api to list missing
registrations. The checker uses the generated operation map plus top-level schema
routes because the installed FastAPI version stores included routers lazily.
It currently reports 110/127 and exits nonzero for the 17 pending operations.
The regular quality checks continue separately while those operations are ported.
Registration coverage measures reachability and still needs business-behavior checks.

Added mute PUT/DELETE endpoints with atomic create/update behavior, preserved creation
time and reason-update rules, self-mute rejection and idempotent removal. A shared
Pydantic request model validates block/mute reasons, including trimming, numeric
string inputs, null/type rejection and the existing 256-character limit. PostgreSQL
HTTP tests exercise mutations, list responses and validation errors. The versioned
OpenAPI endpoint is restored at /api/v1/openapi/ and has a dedicated HTTP regression.

Backend quality passed 741 cases before the final schema-URL regression was added.
The 18 focused request-validation/mute cases passed afterward. Strict typing covers
219 modules. Web checks passed 235 unit and seven browser cases plus the production
build. One earlier combined run hit the existing 30-second workspace browser-test
limit. The same case passed alone in 5.8 seconds and all seven passed in a full web
rerun. Test timeouts and application behavior were left as configured.

The missing operations cover avatar upload, episode progress, own/public reviews,
public library/collection detail/items and generic comment list/create. The comment
service audit also found missing target-type activity support, mute filtering,
notification writes and target/parent lock checks. These semantics require completion
alongside registering those routes before production cutover.

The final backend rerun, including the versioned schema-URL regression, passed all
742 cases with the dedicated Redis case skipped. The HTTP operation inventory still
reports the 17 pending operations described above.

### Review lifecycle and public library resources

Registered own-review list/detail/update/delete, public-review detail, public user/entity
review lists, public library entries and public collection detail/items. Public account
visibility checks apply in both block directions, and public item lists filter private
library entries even when the viewer owns the collection. Library and review DTOs now
validate query choices and review writes with the existing field messages. The library
status choice is drop, matching retained records and the frontend. Date-only watch fields
serialize as dates, and literal search patterns escape SQL wildcards. Collection searches
include notes and preserve secondary ordering.

Review edits lock the review row. The retained Django selector attempted to lock nullable
outer-join rows, causing valid edits/deletes to fail in the reference application.
The temporary comparison oracle restricted that reference lock to its own row before
comparing intended mutation results. With that correction, 53 complete HTTP responses
matched across reads, filtering, all public library ordering choices, validation, writes
and deletion. Generated identifiers and write timestamps were excluded for writes.
The oracle ran entirely inside a rolled-back disposable database transaction.

Alembic revision 0006_content_delete_rules transfers 42 content foreign-key deletion
rules from the former ORM collector into PostgreSQL. The actions preserve the existing
CASCADE/SET NULL contract for library entries, collections, reviews, posts and dependent
community content. A PostgreSQL HTTP regression deletes a review with dependent comments,
reports, notifications and activity, checks immediate foreign-key integrity, preserves
an unrelated review and retains moderation records whose report reference becomes null.
Fresh installation, downgrade to the baseline and upgrade to head passed in a temporary
database, which was removed afterward. Upgrade and downgrade of the new revision passed
in the disposable integration database, and the restored production copy upgraded to head.
Production itself has received no schema change in this step.

The frontend decoder accepts finite numeric API ratings and normalizes them to its
existing decimal-string representation. Prior response tests covered null ratings and
missed numeric values, causing rated library entries to fail decoding. Nine regression
cases now cover numeric/string/null inputs and invalid values. OpenAPI was regenerated.
Root checks passed 754 backend cases, one optional Redis case skipped, strict typing of
224 modules, 244 frontend unit cases, seven browser cases and the remaining build/lint
checks. HTTP operation inventory is 120/127. The remaining operations are avatar upload,
episode progress GET/replace/set/delete and generic comment list/create. Deployment,
remaining mutation semantics and retirement work remain part of the active goal.

### Episode-progress operations

Added read, bounded replacement, single-episode completion and idempotent removal
through the existing library paths. Writes lock the owning entry and preserve atomic
replacement when an insert fails. Episode discovery reuses the current-relation read
model, includes both sides of a work's merge cluster and retains the existing handling
of private active episodes and stored completion rows that are no longer listed.
Duplicate requested identifiers are removed after the 5000-item validation limit.

Nested validation errors retain index keys instead of flattening list errors into dotted
field names. ProblemDocument describes the recursive error tree, and its definitions
are merged into OpenAPI components so every schema reference resolves. Frontend progress
contracts accept numeric or null episode facts and normalize them for existing controls.
An absent episode number remains absent instead of becoming zero in the UI.

Ten PostgreSQL cases cover all progress operations, membership/ownership failures,
merge clusters, historical rows, nested validation, limits and rollback after an insert
failure. Twenty full HTTP responses matched a rollback-only Django oracle, including
facts, merged works, private/retired episodes, historical completion rows and errors.
The oracle restricted the old nullable-join selector lock to the entry row to exercise
its intended write behavior. The disposable HTTP fixture now rolls back failed requests
as the real dependency does. Its blocked-account setup commits the relationship before
checking several successive rejected requests, preventing test setup from being rolled
back by the first expected error.

Root checks passed 764 backend cases, with the dedicated Redis case skipped, strict
typing of 226 modules, 245 frontend unit cases, browser checks and the production build.
OpenAPI was regenerated. HTTP registration coverage is 124/127. Avatar upload and generic
comment GET/POST remain to be ported, followed by the remaining behavior/configuration,
production deployment and retirement work under the active goal.

### Generic comments and durable interaction effects

Registered generic comment GET/POST and moved comment routes into their own API module.
Typed comment requests cover content, target/parent identifiers, visibility, spoiler
flags, edits and moderation. Activity targets are now included in comment payloads.
Public activity access checks inherit the visibility of related entries, reviews and
collections. Comment lists filter muted authors and both block directions. Creation
checks target/parent locks and block relationships before writing.

Comment creation, post/parent reply counts, activity and recipient notification are
one transaction. Target locks precede comment locks across create/edit/delete paths.
Deleting a leaf decrements post/parent counters, while retaining a hidden parent with
replies also hides its feed activity. Editing or deleting another author's comment
returns the existing permission-denied problem. Self-notifications are omitted and
replies notify the parent author. The existing nested post-comment path uses the same
context service as the generic path.

Twenty PostgreSQL cases exercise all four target types, activity/notification metadata,
reply recipients, private-resource visibility, muted/blocked authors, locks, permissions,
validation and rollback after a notification-insert failure. Twenty simultaneous HTTP
requests through independent PostgreSQL connections all created comments and left exactly
20 comments, 20 activities, 20 notifications and a post reply count of 20. Temporary
committed rows were removed after that concurrency case.

A rollback-only oracle matched 34 complete legacy HTTP responses and comment creation
side effects. Generated write identifiers and timestamps were normalized for comparison.
The frontend decoder regression covers activity targets and hidden parent records.
Root checks passed 784 backend cases, with one optional Redis case skipped, strict typing
of 228 modules, 246 web unit cases, browser checks and the production build. OpenAPI was
regenerated. Registration coverage is 126/127, leaving avatar upload before the remaining
behavior/configuration review, rollout and retirement work.

### Avatar upload and complete HTTP registration

Registered multipart avatar upload with Pillow image verification and python-multipart
parsing. The service reads the retained size and content-type settings, detects MIME
from image bytes, checks supported image extensions and stores a generated filename
using the detected format. Empty/corrupt/unsupported images and request encodings retain
the existing field problems. Storage errors return users.avatar_upload_failed with 502.
Uploads and object cleanup run outside database row locks through the existing boto3
S3 adapter. API profile/settings reads now share a context-owned default-profile service
that tolerates concurrent creation and reserved default nicknames.

Avatar replacement reads the current URL under a profile lock, commits its new reference
and then removes an owned prior object. Failed profile writes remove the unreferenced
new upload. After an uncertain commit, cleanup verifies the reference and retains the
object if the outcome cannot be established, preventing a durable URL from pointing at
a deleted object. This can retain an unreferenced object during a simultaneous database
outage. Deletion accepts only the configured storage origin/bucket and the account's
avatar prefix. External avatar URLs are preserved.

Fourteen avatar cases plus storage regressions exercise multipart requests, JPEG/PNG/WebP,
MIME detection, limits, invalid data, profile creation/collision, failed uploads, failed
profile writes and uncertain commit responses. S3 calls use botocore stubs in this run.
The browser API-client regression verifies native FormData with bearer authentication
and credentials. Live object-storage and production runtime verification remain pending.
Implementation references are the official FastAPI request-files and Pillow Image docs.

HTTP registration is now 127/127. The route inventory check is included in both the local
API check and CI, alongside worker task and queue contracts. Root checks passed 799 backend
cases, one optional Redis case skipped, strict typing of 230 modules, 247 frontend unit
cases, seven browser cases and the production build. OpenAPI was regenerated. Complete
registration does not finish the remaining request/mutation/configuration audit, production
rollout or old runtime/schema retirement under the active goal.

### Framework schema retirement

Alembic renames the refresh token and revocation tables, their sequences and
constraints, and the revocation timestamp in place. The production rehearsal
retained 1,390 issued tokens and 847 revocations across the rename and rollback.
The runtime signing key is supplied as `JWT_SECRET` with its existing value.

The next revision removes the nine old framework tables. It locks and checks
group, grant, admin log and session tables before removing any of them. The
production copy contains no records in these tables. Generated permissions,
content types and migration metadata are retained in the pre-upgrade backup.
Restore that backup to recover the retired framework schema.

The following revision removes ten transitional views over the canonical
catalogue, matching and library tables. Runtime SQL uses the canonical tables.
The views contained no data and had no dependent production objects. Their
upgrade and downgrade were verified on the production copy and the fresh
PostgreSQL test schema.
