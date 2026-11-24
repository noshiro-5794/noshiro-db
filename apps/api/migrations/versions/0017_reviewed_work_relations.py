"""Project previously reviewed same-season decisions as catalogue relations."""

from alembic import op

revision = "0017_reviewed_work_relations"
down_revision = "0016_calendar_ranking"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO entity_relation
          (from_entity_id, to_entity_id, relation_type, qualifiers, created_at, updated_at)
        SELECT edge.source, edge.target, 'same-season', jsonb_build_object('reviewed', true),
               min(decision.created_at), now()
        FROM match_candidate AS candidate
        JOIN candidate_decision AS decision ON decision.candidate_id = candidate.id
        JOIN entity AS lhs ON lhs.id = candidate.left_entity_id AND lhs.kind = 'work'
        JOIN entity AS rhs ON rhs.id = candidate.right_entity_id AND rhs.kind = 'work'
        CROSS JOIN LATERAL (VALUES (lhs.id, rhs.id), (rhs.id, lhs.id)) AS edge(source, target)
        WHERE candidate.status = 'grouped' AND decision.outcome = 'group'
          AND edge.source <> edge.target
        GROUP BY edge.source, edge.target
        ON CONFLICT (from_entity_id, to_entity_id, relation_type) DO NOTHING
        """
    )


def downgrade() -> None:
    raise RuntimeError("Restore a pre-migration backup to recover the earlier grouping policy.")
