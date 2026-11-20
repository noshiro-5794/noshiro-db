"""Source-specific anime profile updates and provenance-scoped external links."""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.presentation.fragments import fetch


def parse_iso_date(value: Any) -> date | None:
    """A provider date as a ``date``, or None when it is not a usable date.

    MAL emits ``"2026-01-05"`` for a known date and an empty string otherwise. A ``date``
    is returned rather than the string because the driver binds DATE parameters from
    objects, not text.
    """
    if not isinstance(value, str) or len(value) < 10:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


async def upsert_anime_profile(
    session: AsyncSession,
    *,
    work_entity_id: Any,
    media_format: str = "",
    episode_count: int | None = None,
    premiered_on: date | None = None,
    ended_on: date | None = None,
    source_material: str | None = None,
    replace_metadata: bool = False,
    replace_episode_count: bool = False,
) -> None:
    """Write profile metadata and retain unavailable broadcast dates.

    ``replace_metadata`` replaces format and episode count even when empty.
    An omitted source-material value preserves the existing source material.
    """
    await fetch(
        session,
        """
        INSERT INTO anime_profile
          (work_id, format, source_material, episode_count, premiered_on, ended_on,
           created_at, updated_at)
        VALUES (:work, :format, COALESCE(:source, ''), :episodes, :premiered, :ended, now(), now())
        ON CONFLICT (work_id) DO UPDATE
          SET format = CASE WHEN :replace_metadata THEN EXCLUDED.format
                            WHEN EXCLUDED.format = '' THEN anime_profile.format
                            ELSE EXCLUDED.format END,
              episode_count = CASE WHEN :replace_metadata OR :replace_episode_count
                                   THEN EXCLUDED.episode_count
                                   ELSE COALESCE(EXCLUDED.episode_count,
                                                 anime_profile.episode_count) END,
              source_material = COALESCE(:source, anime_profile.source_material),
              premiered_on = COALESCE(EXCLUDED.premiered_on,
                                      anime_profile.premiered_on),
              ended_on = COALESCE(EXCLUDED.ended_on, anime_profile.ended_on),
              updated_at = now()
        RETURNING work_id
        """,
        {
            "work": work_entity_id,
            "format": media_format or "",
            "episodes": episode_count,
            "premiered": premiered_on,
            "ended": ended_on,
            "source": source_material,
            "replace_metadata": replace_metadata,
            "replace_episode_count": replace_episode_count,
        },
    )


async def upsert_external_link(
    session: AsyncSession,
    *,
    entity_id: Any,
    provider_record_id: Any,
    observation_id: Any,
    url: str,
    label: str = "",
    link_type: str = "",
) -> None:
    if not url:
        return
    await fetch(
        session,
        """
        INSERT INTO external_link
          (url, label, link_type, entity_id, provider_record_id, observation_id,
           created_at, updated_at)
        VALUES (:url, :label, :link_type, :entity, :record, :observation,
                now(), now())
        ON CONFLICT (entity_id, url, provider_record_id, observation_id) DO UPDATE
          SET label = CASE WHEN EXCLUDED.label = '' THEN external_link.label
                           ELSE EXCLUDED.label END,
              updated_at = now()
        RETURNING id
        """,
        {
            "url": url,
            "label": label,
            "link_type": link_type,
            "entity": entity_id,
            "record": provider_record_id,
            "observation": observation_id,
        },
    )


__all__ = ["parse_iso_date", "upsert_anime_profile", "upsert_external_link"]
