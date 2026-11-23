"""Address immutable metadata proposals by revision and content."""

from alembic import op

revision = "0018_immutable_metadata"
down_revision = "0017_reviewed_work_relations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP INDEX uq_metadata_revision_draft_input")
    op.execute("ALTER TABLE entity_metadata_revision ADD COLUMN proposal_hash char(64)")
    op.execute(
        """
        UPDATE entity_metadata_revision SET proposal_hash =
          encode(sha256(convert_to('imported:' || id::text, 'UTF8')), 'hex')
        """
    )
    op.execute(
        """
        ALTER TABLE entity_metadata_revision
          ALTER COLUMN proposal_hash SET NOT NULL,
          ADD CONSTRAINT uq_metadata_revision_proposal
            UNIQUE (entity_id, language, input_hash, proposal_hash)
        """
    )


def downgrade() -> None:
    raise RuntimeError("Restore a pre-migration backup to recover the single-draft schema.")
