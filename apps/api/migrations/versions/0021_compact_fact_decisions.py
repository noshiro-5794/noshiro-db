"""Coalesce consecutive, equivalent fact decisions without removing real transitions."""

from alembic import op

revision = "0021_compact_fact_decisions"
down_revision = "0020_retire_projections"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        WITH boundaries AS (
            SELECT id, entity_id, predicate_id, language,
                   CASE WHEN NOT lag(is_active) OVER history
                        AND created_at = lag(updated_at) OVER history
                        AND selected_fact_id IS NOT DISTINCT FROM lag(selected_fact_id) OVER history
                        AND policy_version = lag(policy_version) OVER history
                        AND reason = lag(reason) OVER history
                        THEN 0 ELSE 1 END AS starts_interval
            FROM resolution_decision
            WINDOW history AS (PARTITION BY entity_id, predicate_id, language ORDER BY id)
        ),
        intervals AS MATERIALIZED (
            SELECT id,
                   min(id) OVER interval AS first_id,
                   max(id) OVER interval AS last_id
            FROM (
                SELECT *, sum(starts_interval) OVER (
                    PARTITION BY entity_id, predicate_id, language ORDER BY id
                ) AS interval_id
                FROM boundaries
            ) AS numbered
            WINDOW interval AS (PARTITION BY entity_id, predicate_id, language, interval_id)
        ),
        preserve_start AS (
            UPDATE resolution_decision AS retained
            SET created_at = first_decision.created_at
            FROM intervals JOIN resolution_decision AS first_decision
              ON first_decision.id = intervals.first_id
            WHERE intervals.id = intervals.last_id AND intervals.first_id <> intervals.last_id
              AND retained.id = intervals.last_id
        )
        DELETE FROM resolution_decision AS obsolete
        USING intervals
        WHERE obsolete.id = intervals.id AND intervals.id <> intervals.last_id
        """
    )


def downgrade() -> None:
    raise RuntimeError("Restore a pre-migration backup to recover redundant decision rows.")
