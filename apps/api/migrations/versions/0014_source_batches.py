"""Identify complete catalogue fetches for deterministic offline replay."""

from alembic import op

revision = "0014_source_batches"
down_revision = "0013_metadata_publication"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE ingest.source_batch (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            provider_id bigint NOT NULL REFERENCES provider(id),
            external_id text NOT NULL CHECK (length(external_id) > 0),
            started_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            completed_at timestamptz,
            CHECK (completed_at >= started_at)
        )
        """
    )
    op.execute(
        """
        ALTER TABLE ingest.source_fetch
            ADD COLUMN batch_id uuid REFERENCES ingest.source_batch(id) ON DELETE SET NULL,
            ADD COLUMN request_hash text CHECK (request_hash ~ '^[0-9a-f]{64}$'),
            ADD CHECK (batch_id IS NULL OR request_hash IS NOT NULL)
        """
    )
    op.execute(
        """
        CREATE INDEX ix_source_batch_provider_work
            ON ingest.source_batch (provider_id, external_id, started_at DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX ix_source_fetch_batch_request
            ON ingest.source_fetch (batch_id, request_hash, fetched_at)
            WHERE batch_id IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE ingest.source_fetch DROP COLUMN batch_id, DROP COLUMN request_hash")
    op.execute("DROP TABLE ingest.source_batch")
