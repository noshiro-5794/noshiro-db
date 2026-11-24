# Database migrations

Alembic owns the PostgreSQL schema. From `apps/api`, configure
`DATABASE_URL` and run `make migrate`. A fresh PostgreSQL 18 database starts
with the schema-only baseline and advances to `head`.

## Existing databases

Existing Alembic-managed databases apply pending revisions in order. Record the
current revision and create a verified backup before a production migration.
For catalogue upgrades from `0009`, stop catalogue writes and drain the worker
queues before switching versions. Run the migration, then start the API and
workers from the same release. The migration preserves work UUIDs, source
revisions, reviewed metadata, and historical calendar engagement, and removes
the replaced ranking and display structures. Inspect unversioned databases
against the baseline before explicitly stamping them.

```sh
uv run alembic current
uv run alembic history
make migrate
```

## Recovery

The migration source identifies the revisions that require backup-based
recovery, including the ranking and metadata replacements.
The remaining revisions describe their downgrade behavior in the migration
source. Test recovery on a restored copy before using it on production data.

Revisions `0020` and `0021` remove redundant data. The visual novel profile
retirement verifies that source revisions still contain its stored values.
Fact-decision compaction preserves real changes, including a return to a
previous decision after a different value or a gap. Measure the compaction on
a restored copy with production-scale history before scheduling the upgrade.

The migration history includes the Django retirement, refresh-token table
renames, and transitional view removal. [Historical migration records](history/README.md)
