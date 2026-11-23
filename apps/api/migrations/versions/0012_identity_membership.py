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
    op.execute("UPDATE fact SET status='candidate' WHERE status='selected'")


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
