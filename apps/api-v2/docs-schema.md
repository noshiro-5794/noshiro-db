# Schema ownership

Revision `0001_baseline` records the schema Django built. It has no operations:
the tables already exist. What it changes is who writes DDL from now on.

```
$ alembic history
<base> -> 0001_baseline (head), Baseline: the schema Django built.

$ alembic current
0001_baseline (head)
```

The production database is stamped at that revision (`alembic_version`), so every
later revision applies on top of the schema as it exists today.

## Transition rule

While both services run:

1. **DDL is Alembic's.** New tables, columns, indexes, views and data moves are
   written as revisions here — never as a Django migration.
2. **Django models follow the database.** When a column changes, the model is
   updated so the old service keeps serving, and the Django migration that
   `makemigrations` wants is written as `SeparateDatabaseAndState` with **no
   database operations**: it only moves Django's internal state.
3. **No new Django-native DDL** — a second history would make "what is the
   schema" ambiguous, which is the problem this change removes.

After the cutover the Django app is deleted and only this history remains.

## Revisions

| Revision | What | Verified |
|---|---|---|
| `0001_baseline` | the schema Django built, no operations | `stamp` on production |
| `0002_display_profile` | `entity_display_profile` | applied, downgraded, re-applied on production |
| `0003_metric_tables` | `metric_current`, `metric_daily` + backfill from `metric_snapshot` | applied, downgraded, re-applied; counts reproduce exactly |
| `0004_metric_view` | `entity_metric_current` | applied; 551,018 rows, one per (entity, metric) |

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

Every revision must be reversible or explicitly documented as not being so; the
check that applies it in CI runs `upgrade head` then `downgrade base` on a copy.
