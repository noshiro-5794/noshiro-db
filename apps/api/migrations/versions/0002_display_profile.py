"""Add the display profile: what a page shows for one entity in one language.

The presentation layer, not knowledge. Every value cites the row it came from, so
a reviewer can ask "why this title" and get an answer, and the table can be
dropped and rebuilt from the resolved entity.

Revision 0001 is the inherited schema; this is the first change this service owns.
"""

from __future__ import annotations

from alembic import op

revision: str = "0002_display_profile"
down_revision: str | None = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE entity_display_profile (
            id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            entity_id uuid NOT NULL REFERENCES entity(id) ON DELETE CASCADE,
            language varchar(35) NOT NULL DEFAULT '',
            title_name_id bigint NOT NULL REFERENCES entity_name(id) ON DELETE RESTRICT,
            title_text varchar(512) NOT NULL,
            description_text text NOT NULL DEFAULT '',
            description_source_ids jsonb NOT NULL DEFAULT '[]'::jsonb,
            is_machine_generated boolean NOT NULL DEFAULT false,
            cover_asset_id uuid REFERENCES media_asset(id) ON DELETE SET NULL,
            field_choices jsonb NOT NULL DEFAULT '[]'::jsonb,
            bundle_version varchar(32) NOT NULL DEFAULT 'v1',
            input_hash char(64) NOT NULL,
            model varchar(128) NOT NULL DEFAULT '',
            prompt_version varchar(64) NOT NULL DEFAULT '',
            confidence numeric(5, 4),
            state varchar(16) NOT NULL DEFAULT 'draft',
            reject_reason text NOT NULL DEFAULT '',
            reviewed_by bigint REFERENCES "user"(id) ON DELETE SET NULL,
            reviewed_at timestamptz,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT ck_display_profile_state
                CHECK (state IN ('draft', 'active', 'rejected', 'archived')),
            CONSTRAINT ck_display_profile_confidence
                CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1))
        )
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX uq_display_profile_input
        ON entity_display_profile (entity_id, language, input_hash)
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX uq_display_profile_active
        ON entity_display_profile (entity_id, language)
        WHERE state = 'active'
        """
    )
    op.execute(
        """
        CREATE INDEX ix_display_profile_entity
        ON entity_display_profile (entity_id, language)
        """
    )
    op.execute(
        """
        CREATE INDEX ix_display_profile_state
        ON entity_display_profile (state)
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE entity_display_profile")
