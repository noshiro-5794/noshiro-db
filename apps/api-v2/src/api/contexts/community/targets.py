"""The summary every payload gives for the thing it points at.

A notification, a comment and a report all name a target by type and id, and the
shape depends on the type. This module is where those shapes live so the payload
builders stay about their own fields.
"""

from __future__ import annotations

from typing import Any

from api.contexts.community.people import person

ACTIVITY = "activity"


def activity_target(row: Any) -> dict[str, Any] | None:
    """A timeline entry: who did it and, when it concerns someone, who."""
    if row.activity_id is None:
        return None
    return {
        "type": ACTIVITY,
        "id": row.activity_id,
        "user": person(
            row.activity_user_id,
            row.activity_user_nickname,
            row.activity_user_avatar,
        ),
        "target_user": person(
            row.activity_target_id,
            row.activity_target_nickname,
            row.activity_target_avatar,
        ),
    }
