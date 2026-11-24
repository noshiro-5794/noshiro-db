"""Keep reviewed terminology aliases in the taxonomy context."""

from alembic import op

revision = "0022_scope_taxonomy_aliases"
down_revision = "0021_compact_fact_decisions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.rename_table("index_term_alias", "taxonomy_alias")
    op.execute("DELETE FROM taxonomy_alias WHERE vocabulary = 'legacy' AND term_id IS NULL")
    op.execute("ALTER SEQUENCE index_term_alias_id_seq RENAME TO taxonomy_alias_id_seq")
    op.execute(
        "ALTER TABLE taxonomy_alias RENAME CONSTRAINT index_term_alias_pkey TO taxonomy_alias_pkey"
    )
    op.drop_index("idx_term_alias_lookup", table_name="taxonomy_alias")


def downgrade() -> None:
    raise RuntimeError("Restore a pre-migration backup to recover retired global aliases.")
