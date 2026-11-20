"""Remove transitional views over the renamed catalogue and library tables."""

from alembic import op

revision: str = "0009_retire_schema_aliases"
down_revision: str | None = "0008_retire_django"
branch_labels = None
depends_on = None

VIEWS = (
    ("collection", "user_collection", "id, name, simple_rating, note, user_id, is_public"),
    (
        "collection_item",
        "user_collection_item",
        'id, "order", relation, collection_id, user_subject_id',
    ),
    (
        "index_collection",
        "curated_collection",
        "id, created_at, updated_at, slug, name, is_enabled",
    ),
    (
        "index_entity",
        "entity",
        "created_at, updated_at, id, kind, lifecycle, visibility, audience, spoiler_level",
    ),
    (
        "index_membership",
        "curated_membership",
        "id, created_at, updated_at, listing_state, inclusion_reason, collection_id, entity_id",
    ),
    (
        "match_decision",
        "candidate_decision",
        "id, created_at, updated_at, outcome, decided_by, policy_version, "
        "reason, decision_data, candidate_id",
    ),
    (
        "provider_representation",
        "entity_representation",
        "created_at, updated_at, id, mapping_kind, method, confidence, "
        "is_active, verified_at, entity_id, provider_record_id",
    ),
    (
        "review",
        "user_review",
        "id, title, content, is_spoiler, created_at, user_subject_id, is_public, updated_at",
    ),
    (
        "user_subject",
        "user_library_entry",
        "id, status, simple_rating, rating, comment, watch_start_date, watch_end_date, "
        "is_public, created_at, updated_at, user_id, entity_id",
    ),
    ("user_subject_tag", "user_library_entry_tag", "id, user_subject_id, tag_id"),
)


def upgrade() -> None:
    for name, _, _ in VIEWS:
        op.execute(f"DROP VIEW public.{name}")


def downgrade() -> None:
    for name, table, columns in VIEWS:
        op.execute(f"CREATE VIEW public.{name} AS SELECT {columns} FROM public.{table}")
