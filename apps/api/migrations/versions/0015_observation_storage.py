"""Remove duplicate observation payloads and revision hashes."""

from alembic import op

revision = "0015_observation_storage"
down_revision = "0014_source_batches"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE provider_observation
          ALTER COLUMN normalized_data DROP DEFAULT,
          ALTER COLUMN normalized_data DROP NOT NULL,
          ADD CONSTRAINT ck_observation_payload
            CHECK (normalized_data IS NOT NULL OR mapping_run_id IS NOT NULL)
        """
    )
    op.execute(
        """
        UPDATE provider_observation AS observation SET normalized_data = NULL
        FROM mapping_run AS mapping
        JOIN provider_revision AS revision ON revision.id = mapping.revision_id
        WHERE mapping.id = observation.mapping_run_id
          AND observation.normalized_data = revision.payload
        """
    )
    op.execute(
        """
        UPDATE provider_observation AS observation
        SET normalized_data = jsonb_build_object(
            '_projection_hash', observation.normalized_data -> '_projection_hash'
        )
        FROM mapping_run AS mapping
        JOIN provider_revision AS revision ON revision.id = mapping.revision_id
        WHERE mapping.id = observation.mapping_run_id AND mapping.mapper LIKE 'bangumi.%'
          AND observation.normalized_data ? '_projection_hash'
          AND observation.normalized_data - '_projection_hash' = revision.payload
        """
    )
    op.execute("ALTER TABLE provider_record DROP COLUMN latest_payload_hash")


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE provider_record
          ADD COLUMN latest_payload_hash varchar(64) NOT NULL DEFAULT ''
        """
    )
    op.execute(
        """
        UPDATE provider_record AS record SET latest_payload_hash = revision.payload_hash
        FROM provider_revision AS revision WHERE revision.id = record.latest_revision_id
        """
    )
    op.execute("ALTER TABLE provider_record ALTER COLUMN latest_payload_hash DROP DEFAULT")
    op.execute(
        """
        UPDATE provider_observation AS observation
        SET normalized_data = CASE WHEN observation.normalized_data IS NULL THEN revision.payload
            ELSE revision.payload || observation.normalized_data END
        FROM mapping_run AS mapping JOIN provider_revision AS revision
          ON revision.id = mapping.revision_id
        WHERE mapping.id = observation.mapping_run_id
          AND (observation.normalized_data IS NULL OR (
              mapping.mapper LIKE 'bangumi.%'
              AND jsonb_typeof(observation.normalized_data) = 'object'
              AND observation.normalized_data ? '_projection_hash'
              AND observation.normalized_data - '_projection_hash' = '{}'::jsonb
          ))
        """
    )
    op.execute(
        """
        ALTER TABLE provider_observation
          DROP CONSTRAINT ck_observation_payload,
          ALTER COLUMN normalized_data SET NOT NULL
        """
    )
