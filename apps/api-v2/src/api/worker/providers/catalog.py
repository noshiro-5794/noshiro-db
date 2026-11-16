"""Provider-neutral discovery pages for resumable synchronization."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class CatalogPage:
    external_ids: tuple[str, ...]
    next_cursor: str | None
    total_count: int | None = None


@dataclass(frozen=True, slots=True)
class DeltaPage:
    external_ids: tuple[str, ...]
    next_cursor: str | None
    watermark: str
    upstream_updated_at: datetime | None = None
    total_count: int | None = None
