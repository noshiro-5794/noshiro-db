"""Index campaign work in the order used by bounded fetch and AI stages."""

import sqlalchemy as sa
from alembic import op

revision: str = "0005_campaign_queue_indexes"
down_revision: str | None = "0004_metric_view"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "idx_sync_wi_queued_order",
        "sync_work_item",
        ["campaign_id", "shard", "id"],
        postgresql_where=sa.text("status='queued'"),
    )
    op.create_index(
        "idx_sync_wi_normalize_order",
        "sync_work_item",
        ["campaign_id", "shard", "id"],
        postgresql_where=sa.text("status='succeeded' AND ai_processed_at IS NULL"),
    )
    op.create_index(
        "idx_sync_wi_enrich_order",
        "sync_work_item",
        ["campaign_id", "shard", "id"],
        postgresql_where=sa.text("status='succeeded' AND ai_enriched_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("idx_sync_wi_enrich_order", table_name="sync_work_item")
    op.drop_index("idx_sync_wi_normalize_order", table_name="sync_work_item")
    op.drop_index("idx_sync_wi_queued_order", table_name="sync_work_item")
