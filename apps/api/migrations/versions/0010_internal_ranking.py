"""Keep external engagement in a single internal signal store."""

from alembic import op

revision = "0010_internal_ranking"
down_revision = "0009_retire_schema_aliases"
branch_labels = None
depends_on = None

METRICS = """
    ('mal-score', 'score'),
    ('mal-rank', 'rank'),
    ('mal-members', 'members'),
    ('mal-popularity', 'popularity'),
    ('anilist-average-score', 'score'),
    ('anilist-favourites', 'favourites'),
    ('anilist-popularity', 'popularity'),
    ('anilist-trending', 'trending'),
    ('comment-count', 'comment-count'),
    ('playtime-votes', 'playtime-votes')
"""


def upgrade() -> None:
    op.execute("CREATE SCHEMA ranking")
    op.execute("ALTER TABLE public.metric_snapshot SET SCHEMA ranking")
    op.rename_table("metric_snapshot", "provider_metric", schema="ranking")
    op.execute(
        """
        CREATE TABLE ranking.entity_rank (
            entity_id uuid PRIMARY KEY REFERENCES public.work(entity_id) ON DELETE CASCADE,
            score numeric(12, 6) NOT NULL CHECK (score BETWEEN 0 AND 100),
            refreshed_at timestamptz NOT NULL
        )
        """
    )
    op.execute(
        """
        INSERT INTO ranking.entity_rank (entity_id, score, refreshed_at)
        SELECT entity_id, popularity, COALESCE(popularity_refreshed_at, updated_at)
        FROM work
        WHERE popularity_refreshed_at IS NOT NULL OR popularity <> 0
        """
    )
    op.execute(
        f"""
        WITH internal_predicate(slug, metric) AS (VALUES {METRICS})
        INSERT INTO ranking.provider_metric
            (metric, value, observed_at, entity_id, provider_record_id)
        SELECT internal_predicate.metric, (fact.value #>> '{{}}')::numeric,
               observation.observed_at, fact.entity_id, observation.provider_record_id
        FROM fact
        JOIN predicate ON predicate.id = fact.predicate_id
        JOIN internal_predicate ON internal_predicate.slug = predicate.slug
        JOIN fact_evidence AS evidence ON evidence.fact_id = fact.id
        JOIN provider_observation AS observation ON observation.id = evidence.observation_id
        WHERE jsonb_typeof(fact.value) = 'number'
        ORDER BY fact.created_at, fact.id
        ON CONFLICT (provider_record_id, metric, observed_at) DO NOTHING
        """
    )
    # Remove engagement facts and selections after preserving their numeric series.
    for table in ("resolution_decision", "fact_evidence", "fact", "predicate"):
        match = {
            "resolution_decision": "predicate_id IN (SELECT id FROM internal_predicate)",
            "fact_evidence": (
                "fact_id IN (SELECT id FROM fact WHERE predicate_id IN"
                " (SELECT id FROM internal_predicate))"
            ),
            "fact": "predicate_id IN (SELECT id FROM internal_predicate)",
            "predicate": "id IN (SELECT id FROM internal_predicate)",
        }[table]
        op.execute(
            f"""
            WITH metric_names(slug, metric) AS (VALUES {METRICS}),
            internal_predicate AS (SELECT id FROM predicate JOIN metric_names USING (slug))
            DELETE FROM {table} WHERE {match}
            """
        )
    op.execute("DROP VIEW public.entity_metric_current")
    op.drop_table("metric_daily")
    op.drop_table("metric_current")
    op.drop_column("work", "popularity")
    op.drop_column("work", "popularity_refreshed_at")


def downgrade() -> None:
    raise RuntimeError("Restore a pre-migration backup to recover retired engagement facts.")
