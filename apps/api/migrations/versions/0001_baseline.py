"""Bootstrap the existing PostgreSQL schema without the retired Django runtime.

Databases already stamped at this revision retain their existing schema. New databases
replay the checked-in schema-only baseline before applying subsequent revisions.
"""

from __future__ import annotations

from pathlib import Path

from alembic import context, op
from sqlalchemy import text

revision: str = "0001_baseline"
down_revision: str | None = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    schema = (Path(__file__).resolve().parents[1] / "baseline.sql").read_text()
    if context.is_offline_mode():
        op.execute(schema)
        return
    connection = op.get_bind()
    exists = connection.execute(text("SELECT to_regclass('public.entity')")).scalar()
    if exists is not None:
        raise RuntimeError(
            "An existing catalogue must be explicitly stamped at 0001_baseline before upgrading."
        )
    # asyncpg's simple-query execution supports the complete DDL batch;
    # prepared execution accepts only a single statement.
    connection.connection.dbapi_connection.run_async(lambda driver: driver.execute(schema))


def downgrade() -> None:
    raise RuntimeError(
        "The schema baseline is irreversible. Restore a database backup to remove it."
    )
