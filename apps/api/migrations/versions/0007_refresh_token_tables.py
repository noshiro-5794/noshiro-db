"""Keep issued and revoked refresh tokens under application-owned names."""

from alembic import op

revision: str = "0007_refresh_token_tables"
down_revision: str | None = "0006_content_delete_rules"
branch_labels = None
depends_on = None

TABLES = {
    "refresh_token": "token_blacklist_outstandingtoken",
    "refresh_token_revocation": "token_blacklist_blacklistedtoken",
}
CONSTRAINTS = (
    ("refresh_token", "pkey", "pkey"),
    ("refresh_token", "jti_hex_d9bdf6f7_uniq", "jti_key"),
    ("refresh_token", "user_id_83bc629a_fk_user_id", "user_id_fkey"),
    ("refresh_token", "id_not_null", "id_not_null"),
    ("refresh_token", "token_not_null", "token_not_null"),
    ("refresh_token", "expires_at_not_null", "expires_at_not_null"),
    ("refresh_token_revocation", "pkey", "pkey"),
    ("refresh_token_revocation", "token_id_key", "token_id_key"),
    ("refresh_token_revocation", "token_id_3cc7fe56_fk", "token_id_fkey"),
    ("refresh_token_revocation", "id_not_null", "id_not_null"),
    ("refresh_token_revocation", "token_id_not_null", "token_id_not_null"),
    ("refresh_token_revocation", "blacklisted_at_not_null", "revoked_at_not_null"),
)


def _rename_objects(*, restore: bool) -> None:
    for table, old_suffix, new_suffix in CONSTRAINTS:
        legacy_table = TABLES[table]
        old, new = f"{legacy_table}_{old_suffix}", f"{table}_{new_suffix}"
        source, target = (new, old) if restore else (old, new)
        op.execute(f"ALTER TABLE {table} RENAME CONSTRAINT {source} TO {target}")

    objects = (
        (
            "INDEX",
            "token_blacklist_outstandingtoken_jti_hex_d9bdf6f7_like",
            "refresh_token_jti_like",
        ),
        ("INDEX", "token_blacklist_outstandingtoken_user_id_83bc629a", "refresh_token_user_id_idx"),
        ("SEQUENCE", "token_blacklist_outstandingtoken_id_seq", "refresh_token_id_seq"),
        (
            "SEQUENCE",
            "token_blacklist_blacklistedtoken_id_seq",
            "refresh_token_revocation_id_seq",
        ),
    )
    for kind, old, new in objects:
        source, target = (new, old) if restore else (old, new)
        op.execute(f"ALTER {kind} {source} RENAME TO {target}")


def upgrade() -> None:
    for new, old in TABLES.items():
        op.rename_table(old, new)
    _rename_objects(restore=False)
    # PostgreSQL 18 derives this name when replaying the schema dump. The
    # live database kept the name assigned before the column was renamed.
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conrelid = 'refresh_token'::regclass
                  AND conname = 'token_blacklist_outstandingtoken_jti_hex_not_null'
            ) THEN
                ALTER TABLE refresh_token RENAME CONSTRAINT
                    token_blacklist_outstandingtoken_jti_hex_not_null
                    TO refresh_token_jti_not_null;
            ELSE
                ALTER TABLE refresh_token RENAME CONSTRAINT
                    token_blacklist_outstandingtoken_jti_not_null
                    TO refresh_token_jti_not_null;
            END IF;
        END
        $$;
        """)
    op.alter_column("refresh_token_revocation", "blacklisted_at", new_column_name="revoked_at")


def downgrade() -> None:
    op.alter_column("refresh_token_revocation", "revoked_at", new_column_name="blacklisted_at")
    _rename_objects(restore=True)
    op.execute(
        "ALTER TABLE refresh_token RENAME CONSTRAINT refresh_token_jti_not_null"
        " TO token_blacklist_outstandingtoken_jti_not_null"
    )
    for new, old in reversed(TABLES.items()):
        op.rename_table(new, old)
