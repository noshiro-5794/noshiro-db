"""Add the signal tables: current value per record and metric, and a daily rollup.

Signals are other sites' users' opinions — scores, ranks, vote counts. They are
not knowledge, they must never reach a page, and they do not belong in `fact`
next to an episode count. These tables give them a home of their own; the values
are copied from `metric_snapshot` so nothing is lost while the old service keeps
reading the snapshot.

The copy is idempotent: rerunning the revision cannot duplicate a row.
"""

from __future__ import annotations

from alembic import op

revision: str = "0003_metric_tables"
down_revision: str | None = "0002_display_profile"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE metric_current (
            provider_record_id uuid NOT NULL
                REFERENCES provider_record(id) ON DELETE CASCADE,
            metric varchar(32) NOT NULL,
            value numeric NOT NULL,
            sample_size integer,
            observed_at timestamptz NOT NULL,
            PRIMARY KEY (provider_record_id, metric)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE metric_daily (
            provider_record_id uuid NOT NULL
                REFERENCES provider_record(id) ON DELETE CASCADE,
            metric varchar(32) NOT NULL,
            day date NOT NULL,
            value numeric NOT NULL,
            samples integer NOT NULL DEFAULT 0,
            PRIMARY KEY (provider_record_id, metric, day)
        )
        """
    )
    op.execute(
        """
        INSERT INTO metric_current (provider_record_id, metric, value, sample_size, observed_at)
        SELECT DISTINCT ON (provider_record_id, metric)
               provider_record_id, metric, value, sample_size, observed_at
        FROM metric_snapshot
        ORDER BY provider_record_id, metric, observed_at DESC
        ON CONFLICT (provider_record_id, metric) DO UPDATE SET
            value = EXCLUDED.value,
            sample_size = EXCLUDED.sample_size,
            observed_at = EXCLUDED.observed_at
        """
    )
    op.execute(
        """
        INSERT INTO metric_daily (provider_record_id, metric, day, value, samples)
        SELECT provider_record_id, metric, observed_at::date, avg(value), count(*)
        FROM metric_snapshot
        GROUP BY provider_record_id, metric, observed_at::date
        ON CONFLICT (provider_record_id, metric, day) DO UPDATE SET
            value = EXCLUDED.value,
            samples = EXCLUDED.samples
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE metric_daily")
    op.execute("DROP TABLE metric_current")
