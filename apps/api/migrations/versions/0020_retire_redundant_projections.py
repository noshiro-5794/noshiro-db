"""Retire unused visual novel profiles and the derived Bangumi tag list."""

from alembic import op

revision = "0020_retire_projections"
down_revision = "0019_work_display_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM galgame_profile AS profile
                WHERE (profile.playtime_minutes IS NOT NULL OR profile.development_status <> '')
                  AND NOT EXISTS (
                    SELECT 1 FROM entity_representation AS representation
                    JOIN provider_record AS record ON record.id = representation.provider_record_id
                    JOIN provider_namespace AS namespace ON namespace.id = record.namespace_id
                    JOIN provider AS provider ON provider.id = namespace.provider_id
                    JOIN provider_revision AS version ON version.record_id = record.id
                    WHERE representation.entity_id = profile.work_id
                      AND provider.slug = 'vndb' AND namespace.slug = 'vn'
                      AND (profile.playtime_minutes IS NULL
                           OR version.payload ->> 'length_minutes' = profile.playtime_minutes::text)
                      AND (profile.development_status = '' OR profile.development_status =
                          CASE version.payload ->> 'devstatus'
                            WHEN '0' THEN 'finished'
                            WHEN '1' THEN 'in-development'
                            WHEN '2' THEN 'cancelled'
                          END)
                  )
            ) THEN
                RAISE EXCEPTION 'Visual novel profile values are missing from source revisions';
            END IF;
        END $$;
        """
    )
    op.drop_table("galgame_profile")
    op.execute(
        """
        DELETE FROM resolution_decision AS decision
        USING predicate
        WHERE predicate.slug = 'provider-tags' AND decision.predicate_id = predicate.id
        """
    )
    op.execute(
        """
        DELETE FROM fact_evidence AS evidence
        USING fact, predicate
        WHERE predicate.slug = 'provider-tags' AND fact.predicate_id = predicate.id
          AND evidence.fact_id = fact.id
        """
    )
    op.execute(
        """
        DELETE FROM fact USING predicate
        WHERE predicate.slug = 'provider-tags' AND fact.predicate_id = predicate.id
        """
    )
    op.execute("DELETE FROM predicate WHERE slug = 'provider-tags'")


def downgrade() -> None:
    raise RuntimeError("Restore a pre-migration backup to recover retired projections.")
