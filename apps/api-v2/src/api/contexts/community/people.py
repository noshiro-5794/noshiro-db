"""The three fields every community payload repeats for a person."""

from __future__ import annotations

from typing import Any


def person(user_id: Any, nickname: Any, avatar: Any) -> dict[str, Any] | None:
    if user_id is None:
        return None
    return {"id": user_id, "nickname": nickname or "", "avatar": avatar or ""}
