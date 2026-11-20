# Schema ownership

Revision `0001_baseline` creates the pre-cutover PostgreSQL schema from
`migrations/baseline.sql`. The schema-only SQL was captured from the repository's
Django migration history applied to an isolated PostgreSQL 18 database. It contains
no user, provider or fixture rows. Fresh installations need only this service and
`alembic upgrade head`.

Existing databases already stamped at 0001 apply only the subsequent revisions.
An unversioned existing database is rejected by the bootstrap; validate it against
the baseline and explicitly `alembic stamp 0001_baseline` before upgrading.

Alembic owns tables, columns, indexes, views and data migrations. Restore a
backup to reverse the schema bootstrap or framework retirement. The bootstrap
creates the core tables. Framework retirement drops the obsolete Django metadata.

## Revisions

| Revision | What | Verified |
|---|---|---|
| `0001_baseline` | schema-only bootstrap for fresh PostgreSQL 18 databases | fresh online and offline installs verified locally; existing stamped installations skip it |
| `0002_display_profile` | `entity_display_profile` | applied, downgraded, re-applied on production |
| `0003_metric_tables` | `metric_current`, `metric_daily` + backfill from `metric_snapshot` | applied, downgraded, re-applied; counts reproduce exactly |
| `0004_metric_view` | `entity_metric_current` | applied; 551,018 rows, one per (entity, metric) |
| `0005_campaign_queue_indexes` | bounded campaign work indexes | production-copy rehearsal and downgrade |
| `0006_content_delete_rules` | database-managed content deletion rules | production-copy rehearsal and downgrade |
| `0007_refresh_token_tables` | application-owned refresh token and revocation tables | reversible rename, production row counts preserved |
| `0008_retire_django` | remove the old framework tables and metadata | production-copy and empty bootstrap rehearsals, rejection with nonempty groups tested |
| `0009_retire_schema_aliases` | remove transitional views over the renamed tables | production-copy and empty bootstrap upgrade and downgrade |

`0003` copies what `metric_snapshot` holds: **551,018** current rows against
551,018 distinct `(record, metric)` keys, **697,636** daily rows against the same
number of distinct `(record, metric, day)` keys, and a spot check against the
latest snapshot. The backfill reruns to the same numbers in nine seconds.

The view answers "what does this entity score now" for the entity's **own**
records: a merged work's sources are represented by their own entities, so a
MAL score reported against a source does not appear under the root. A
cluster-aware aggregate is a query on top of the view, not part of it — the
`/metrics/` endpoint still reads `metric_snapshot`, because switching it would
change a public response.

`0002` was checked three ways on the production database: the table has the
expected 21 columns and 5 indexes; `downgrade -1` removes it and `upgrade head`
restores it; and a second `active` row for the same entity and language is
rejected by `uq_display_profile_active`.

## Commands

```bash
make migrate                 # alembic upgrade head
make revision m="add table"  # new empty revision
uv run alembic downgrade -1  # one step back
```

The schema CI job upgrades through `0007_refresh_token_tables`, downgrades to
`0001_baseline` and then upgrades through the retirement revisions to head on a
fresh PostgreSQL 18 service.
