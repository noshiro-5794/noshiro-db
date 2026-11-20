"""Remove unused framework tables after archiving the production database."""

from alembic import op

revision: str = "0008_retire_django"
down_revision: str | None = "0007_refresh_token_tables"
branch_labels = None
depends_on = None

# Permission definitions, content types and migration records are framework
# metadata. Any grants, groups, admin history or sessions require an explicit
# disposition before the old tables may be removed.
USER_DATA_TABLES = (
    "auth_group",
    "auth_group_permissions",
    "django_admin_log",
    "django_session",
    "user_groups",
    "user_user_permissions",
)
TABLES = (
    "django_admin_log",
    "django_session",
    "user_groups",
    "user_user_permissions",
    "auth_group_permissions",
    "auth_group",
    "auth_permission",
    "django_content_type",
)


def upgrade() -> None:
    op.execute(f"LOCK TABLE {', '.join(USER_DATA_TABLES)} IN ACCESS EXCLUSIVE MODE")
    for table in USER_DATA_TABLES:
        op.execute(f"""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM {table}) THEN
                RAISE EXCEPTION 'Cannot retire Django: % contains records', '{table}';
            END IF;
        END
        $$;
        """)
    for table in TABLES:
        op.drop_table(table)
    # The schema-only baseline excludes the obsolete migration ledger.
    op.drop_table("django_migrations", if_exists=True)


def downgrade() -> None:
    raise RuntimeError("Restore the pre-retirement database backup to recover Django tables.")
