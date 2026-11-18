"""A view that answers "what does this work score now".

`metric_current` is keyed by record, because that is who reported the value. A
work is the merged set of records, so the view joins the active representations
and keeps the latest observation per entity and metric. Internal only: ranking
reads it, a page never does.
"""

from __future__ import annotations

from alembic import op

revision: str = "0004_metric_view"
down_revision: str | None = "0003_metric_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE VIEW entity_metric_current AS
        SELECT DISTINCT ON (representation.entity_id, current.metric)
               representation.entity_id,
               current.metric,
               current.value,
               current.sample_size,
               current.observed_at,
               current.provider_record_id
        FROM metric_current AS current
        JOIN entity_representation AS representation
          ON representation.provider_record_id = current.provider_record_id
         AND representation.is_active
        ORDER BY representation.entity_id, current.metric, current.observed_at DESC
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW entity_metric_current")
