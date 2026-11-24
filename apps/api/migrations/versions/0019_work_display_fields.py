"""Link reviewed display fields to their source facts and occurrences."""

from alembic import op

revision = "0019_work_display_fields"
down_revision = "0018_immutable_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE entity_metadata_field_choice (
            revision_id bigint NOT NULL REFERENCES entity_metadata_revision(id) ON DELETE CASCADE,
            field_key text NOT NULL,
            label text NOT NULL CHECK (length(label) BETWEEN 1 AND 80),
            position smallint NOT NULL CHECK (position >= 0),
            fact_id uuid REFERENCES fact(id) ON DELETE SET NULL,
            observation_id uuid REFERENCES provider_observation(id) ON DELETE SET NULL,
            item_index integer NOT NULL CHECK (item_index >= -1),
            evidence_hash char(64) NOT NULL,
            PRIMARY KEY (revision_id, field_key),
            UNIQUE (revision_id, position)
        )
        """
    )
    op.create_index(
        "ix_metadata_field_choice_observation", "entity_metadata_field_choice", ["observation_id"]
    )


def downgrade() -> None:
    op.execute("DROP TABLE entity_metadata_field_choice")
