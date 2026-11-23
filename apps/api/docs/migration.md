# Database migrations

Alembic owns the PostgreSQL schema. From `apps/api`, configure
`DATABASE_URL` and run `make migrate`. A fresh PostgreSQL 18 database starts
with the schema-only baseline and advances to `head`.

## Existing databases

Existing Alembic-managed databases apply the pending revisions in order.
Record the current revision and create a verified backup before a production
migration. Inspect unversioned databases against the baseline before
explicitly stamping them.

```sh
uv run alembic current
uv run alembic history
make migrate
```

## Recovery

The baseline, framework retirement and internal ranking cleanup revisions
require backup-based recovery.
The remaining revisions describe their downgrade behavior in the migration
source. Test recovery on a restored copy before using it on production data.

The migration history includes the Django retirement, refresh-token table
renames, and transitional view removal. [Historical migration records](history/README.md)
