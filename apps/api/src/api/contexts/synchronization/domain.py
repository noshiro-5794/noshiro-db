"""Campaign transitions and classified work-item failure outcomes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

PROVIDER_NAMESPACES = {"bangumi": "subject", "anilist": "anime", "mal": "anime", "vndb": "vn"}

PHASES = (
    "discovering",
    "fetching",
    "mapping",
    "normalizing",
    "reconciling",
    "enriching",
    "reviewing",
)
ACTIVE = ("queued", *PHASES)
TERMINAL = frozenset({"completed", "cancelled", "paused"})
TRANSITIONS = set(zip(("queued", *PHASES), (*PHASES, "completed"), strict=True))
TRANSITIONS.update((phase, end) for phase in PHASES for end in ("failed", "cancelled", "paused"))
TRANSITIONS.update(("paused", phase) for phase in PHASES)


class LeaseLost(RuntimeError):
    """An expired or replaced lease cannot acknowledge work."""


class UnsupportedAction(ValueError):
    """A campaign control action is unknown."""


@dataclass(frozen=True)
class WorkFailure:
    status: str
    code: str
    message: str
    next_retry_at: datetime | None


def classify_failure(
    error: Exception, *, attempt: int, max_attempts: int, now: datetime
) -> WorkFailure:
    message = f"{type(error).__name__}: {error}"[:4000]
    if getattr(error, "is_not_found", False):
        return WorkFailure("skipped", "not_found", message, None)
    retry_at = None
    status = "failed"
    if getattr(error, "retryable", False) and attempt < max(1, max_attempts):
        retry_after = getattr(error, "retry_after", None)
        delay = retry_after or 30 * (2 ** max(0, attempt - 1))
        retry_at = now + timedelta(seconds=min(delay, 3600))
        status = "queued"
    return WorkFailure(status, type(error).__name__.lower(), message, retry_at)
