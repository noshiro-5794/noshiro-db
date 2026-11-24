"""Store reviewed work metadata separately from its publication pointer."""

from alembic import op

revision = "0013_metadata_publication"
down_revision = "0012_identity_membership"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE entity_display_profile RENAME TO entity_metadata_revision")
    op.execute("DROP INDEX uq_display_profile_active")
    op.execute("DROP INDEX uq_display_profile_input")
    op.execute("DROP INDEX ix_display_profile_entity")
    op.execute("ALTER INDEX ix_display_profile_state RENAME TO ix_metadata_revision_state")
    op.execute("ALTER TABLE entity_metadata_revision DROP CONSTRAINT ck_display_profile_state")
    op.execute(
        "ALTER TABLE entity_metadata_revision RENAME CONSTRAINT ck_display_profile_confidence "
        "TO ck_metadata_revision_confidence"
    )
    op.execute(
        """
        ALTER TABLE entity_metadata_revision
          ADD UNIQUE (entity_id, language, id),
          ADD COLUMN agent_step_id uuid REFERENCES agent_step(id) ON DELETE SET NULL
        """
    )
    op.execute(
        """
        CREATE TABLE entity_metadata_publication (
          entity_id uuid NOT NULL,
          language varchar(35) NOT NULL,
          revision_id bigint NOT NULL,
          published_at timestamptz NOT NULL DEFAULT now(),
          PRIMARY KEY (entity_id, language),
          FOREIGN KEY (entity_id, language, revision_id)
            REFERENCES entity_metadata_revision (entity_id, language, id) ON DELETE CASCADE
        )
        """
    )
    op.execute(
        """
        CREATE TABLE entity_metadata_citation (
          revision_id bigint NOT NULL REFERENCES entity_metadata_revision(id) ON DELETE CASCADE,
          position integer NOT NULL CHECK (position > 0),
          description_id bigint REFERENCES entity_description(id) ON DELETE SET NULL,
          evidence_hash char(64),
          PRIMARY KEY (revision_id, position),
          CHECK (description_id IS NULL OR evidence_hash IS NOT NULL)
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_metadata_citation_description ON entity_metadata_citation(description_id)"
    )
    op.execute(
        """
        INSERT INTO entity_metadata_publication (entity_id, language, revision_id, published_at)
        SELECT entity_id, language, id, COALESCE(reviewed_at, updated_at)
        FROM entity_metadata_revision WHERE state = 'active'
        """
    )
    op.execute(
        """
        INSERT INTO entity_metadata_citation (revision_id, position, description_id, evidence_hash)
        SELECT revision.id, reference.position, description.id,
               encode(sha256(convert_to(left(description.text, 1500), 'UTF8')), 'hex')
        FROM entity_metadata_revision AS revision
        CROSS JOIN LATERAL jsonb_array_elements_text(
            CASE WHEN jsonb_typeof(revision.description_source_ids) = 'array'
              THEN revision.description_source_ids ELSE '[]'::jsonb END
        ) WITH ORDINALITY AS reference(id, position)
        LEFT JOIN entity_description AS description ON description.id =
          CASE WHEN reference.id ~ '^[0-9]{1,19}$'
               THEN CASE WHEN reference.id::numeric <= 9223372036854775807
                         THEN reference.id::bigint END END
        """
    )
    op.execute(
        """
        UPDATE entity_metadata_revision SET state = 'approved'
        WHERE state IN ('active', 'archived')
        """
    )
    op.execute(
        """
        ALTER TABLE entity_metadata_revision
          ADD CONSTRAINT ck_metadata_revision_state
            CHECK (state IN ('draft', 'approved', 'rejected')),
          DROP COLUMN description_source_ids,
          DROP COLUMN field_choices
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX uq_metadata_revision_draft_input
        ON entity_metadata_revision (entity_id, language, input_hash) WHERE state = 'draft'
        """
    )


def downgrade() -> None:
    raise RuntimeError("Restore a pre-upgrade backup to recover the legacy display profile schema.")
