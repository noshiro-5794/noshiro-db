"""Archive provider responses and link them to parsed record revisions."""

from alembic import op

revision = "0011_source_archive"
down_revision = "0010_internal_ranking"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA ingest")
    op.execute(
        """
        CREATE TABLE ingest.source_document (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            provider_id bigint NOT NULL REFERENCES public.provider(id),
            body_hash text NOT NULL CHECK (body_hash ~ '^[0-9a-f]{64}$'),
            body bytea NOT NULL,
            UNIQUE (provider_id, body_hash)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE ingest.source_fetch (
            id uuid PRIMARY KEY,
            document_id uuid NOT NULL REFERENCES ingest.source_document(id),
            endpoint text NOT NULL CHECK (left(endpoint, 1) = '/'),
            method text NOT NULL,
            status_code smallint NOT NULL CHECK (status_code BETWEEN 200 AND 299),
            content_type text NOT NULL,
            fetched_at timestamptz NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE TABLE ingest.revision_source (
            revision_id uuid NOT NULL REFERENCES public.provider_revision(id) ON DELETE CASCADE,
            fetch_id uuid NOT NULL REFERENCES ingest.source_fetch(id),
            json_pointer text NOT NULL CHECK (json_pointer = '' OR left(json_pointer, 1) = '/'),
            PRIMARY KEY (revision_id, fetch_id, json_pointer)
        )
        """
    )
    op.create_index("ix_source_fetch_document", "source_fetch", ["document_id"], schema="ingest")
    op.create_index("ix_revision_source_fetch", "revision_source", ["fetch_id"], schema="ingest")


def downgrade() -> None:
    raise RuntimeError("Restore a pre-migration backup to remove original response archives.")
