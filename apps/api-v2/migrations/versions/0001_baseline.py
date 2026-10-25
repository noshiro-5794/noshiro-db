"""Baseline: the schema Django built.

No operations. The tables, constraints and indexes already exist; this revision
only records the moment the new service takes over the revision history, so the
first real change can be written as a diff against it.
"""

from __future__ import annotations

revision: str = "0001_baseline"
down_revision: str | None = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
