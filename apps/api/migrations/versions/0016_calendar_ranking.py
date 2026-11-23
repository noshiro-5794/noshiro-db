"""Keep external calendar engagement in private ranking storage."""

from alembic import op

revision = "0016_calendar_ranking"
down_revision = "0015_observation_storage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE ranking.provider_metric
          DROP CONSTRAINT uq_metric_snapshot_time,
          ALTER COLUMN provider_record_id DROP NOT NULL,
          ADD CONSTRAINT uq_provider_metric_sample UNIQUE NULLS NOT DISTINCT
            (provider_record_id, entity_id, metric, observed_at)
        """
    )
    op.execute(
        """
        INSERT INTO ranking.provider_metric
            (metric, value, observed_at, entity_id, provider_record_id)
        SELECT 'calendar-watching', max(event.collection_doing),
               COALESCE(observation.observed_at, event.created_at),
               event.work_id, observation.provider_record_id
        FROM airing_event AS event
        LEFT JOIN provider_observation AS observation ON observation.id = event.observation_id
        WHERE event.collection_doing > 0
        GROUP BY COALESCE(observation.observed_at, event.created_at),
                 event.work_id, observation.provider_record_id
        ON CONFLICT (provider_record_id, entity_id, metric, observed_at) DO NOTHING
        """
    )
    op.drop_column("airing_event", "collection_doing")


def downgrade() -> None:
    raise RuntimeError("Restore a pre-migration backup to recover legacy calendar engagement.")
