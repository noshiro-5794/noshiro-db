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

## The shadow comparison that has been run

Same fixture payload through the Django importer and through the port, one transaction per
side, both rolled back. Compared: names, descriptions, media, work type, profile, links,
facts, metrics.

Result: **all equal**, after the comparison found one real divergence — Django uppercases
the media type (`TV`), the port was storing `tv`. Nothing else differed.

Reproduce it with `scripts/shadow_import.sh` (fixture in `scripts/fixtures/mal_anime.json`).

## How far along

`python scripts/task_coverage.py` prints the number: **5 of 23 tasks**, counting only the
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
