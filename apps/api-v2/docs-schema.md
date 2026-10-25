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

## Commands

```bash
make migrate                 # alembic upgrade head
make revision m="add table"  # new empty revision
uv run alembic downgrade -1  # one step back
```

Every revision must be reversible or explicitly documented as not being so; the
check that applies it in CI runs `upgrade head` then `downgrade base` on a copy.
