"""Keep identity membership independent of the entity lifecycle."""

from alembic import op

revision = "0012_identity_membership"
down_revision = "0011_source_archive"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.rename_table("entity_redirect", "entity_identity_membership")
    op.execute(
        """
        UPDATE entity SET lifecycle = 'active'
        WHERE lifecycle = 'merged' AND EXISTS (
            SELECT 1 FROM entity_identity_membership AS membership
            WHERE membership.source_entity_id = entity.id AND membership.is_active
        )
        """
    )
    op.execute(
        "ALTER INDEX uq_active_entity_redirect_source "
        "RENAME TO uq_active_identity_membership_source"
    )
    # A table rewrite rebuilds the indexes once. Historical installations have
    # selected status on most rows, making an indexed UPDATE far more expensive.
    op.execute("SET CONSTRAINTS ALL IMMEDIATE")
    op.execute(
        """
        ALTER TABLE fact ALTER COLUMN status TYPE varchar(16)
        USING (CASE WHEN status = 'selected' THEN 'candidate' ELSE status END)
        """
    )
    op.execute("SET CONSTRAINTS ALL DEFERRED")


def downgrade() -> None:
    op.execute(
        "UPDATE fact SET status='selected' WHERE status='candidate' AND EXISTS ("
        "SELECT 1 FROM resolution_decision WHERE selected_fact_id=fact.id AND is_active)"
    )
    op.execute(
        """
        UPDATE entity SET lifecycle = 'merged'
        WHERE lifecycle = 'active' AND EXISTS (
            SELECT 1 FROM entity_identity_membership AS membership
            WHERE membership.source_entity_id = entity.id AND membership.is_active
        )
        """
    )
    op.execute(
        "ALTER INDEX uq_active_identity_membership_source "
        "RENAME TO uq_active_entity_redirect_source"
    )
    op.rename_table("entity_identity_membership", "entity_redirect")
