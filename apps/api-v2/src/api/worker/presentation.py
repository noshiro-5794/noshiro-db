"""What a visitor actually sees: names, descriptions, artwork, and the collection a work is
listed in.

Ported from the presentation half of `KnowledgeIngestionService`. Two properties matter:

* Everything is keyed by provenance. A name or description is unique per
  ``(entity, text/language, provider_record, observation)``, so re-importing the same
  payload marks the same row instead of appending a duplicate, and two providers supplying
  the same name keep their own rows.
* An empty value records nothing. A provider that does not publish a description must not
  create an empty one that then competes with the mapped facts.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.presentation.fragments import fetch

ORIGINAL = "original"
TRANSLATED = "translated"
UNKNOWN_SAFETY = "unknown"

LISTED = "listed"


async def replace_names(
    session: AsyncSession,
    *,
    entity_id: Any,
    provider_record_id: Any,
    observation_id: Any,
    original: str = "",
    localized: str = "",
) -> int:
    """Record the original title, and the Chinese one when it differs."""
    written = 0
    entries: list[tuple[str, str, str, str, bool]] = []
    if original:
        entries.append((original, "", "", ORIGINAL, True))
    if localized and localized != original:
        entries.append((localized, "zh-Hans", "Hans", TRANSLATED, False))
    for text, language, script, kind, is_original in entries:
        rows = await fetch(
            session,
            """
            INSERT INTO entity_name
              (text, language, script, region, kind, is_official, is_original,
               is_machine_generated, is_reviewed, entity_id, provider_record_id,
               observation_id, created_at, updated_at)
            VALUES (:text, :language, :script, '', :kind, false,
                    :is_original, false, false, :entity, :record, :observation,
                    now(), now())
            ON CONFLICT DO NOTHING
            RETURNING id
            """,
            {
                "text": text,
                "language": language,
                "script": script,
                "kind": kind,
                "is_original": is_original,
                "entity": entity_id,
                "record": provider_record_id,
                "observation": observation_id,
            },
        )
        written += len(rows)
    return written


async def upsert_description(
    session: AsyncSession,
    *,
    entity_id: Any,
    provider_record_id: Any,
    observation_id: Any,
    text: str,
) -> bool:
    """One description per (entity, language, provider, observation)."""
    if not text:
        return False
    await fetch(
        session,
        """
        INSERT INTO entity_description
          (text, language, is_official, is_machine_generated, is_reviewed,
           spoiler_level, safety, entity_id, provider_record_id, observation_id,
           created_at, updated_at)
        VALUES (:text, '', false, false, false, 0, :safety,
                :entity, :record, :observation, now(), now())
        ON CONFLICT (entity_id, language, provider_record_id, observation_id)
        DO UPDATE SET text = EXCLUDED.text, updated_at = now()
        RETURNING id
        """,
        {
            "text": text,
            "safety": UNKNOWN_SAFETY,
            "entity": entity_id,
            "record": provider_record_id,
            "observation": observation_id,
        },
    )
    return True


async def upsert_media(
    session: AsyncSession,
    *,
    entity_id: Any,
    provider_record_id: Any,
    observation_id: Any,
    original: str = "",
    thumbnail: str = "",
) -> int:
    """Poster and thumbnail, each as an asset shared by URL and provider record."""
    written = 0
    for purpose, url in (("poster", original), ("thumbnail", thumbnail)):
        if not url:
            continue
        asset = await fetch(
            session,
            """
            INSERT INTO media_asset
              (id, url, media_type, safety, spoiler_level, provider_record_id,
               created_at, updated_at)
            VALUES (gen_random_uuid(), :url, 'image', :safety, 0, :record, now(), now())
            ON CONFLICT (url, provider_record_id) DO UPDATE SET url = EXCLUDED.url
            RETURNING id
            """,
            {"url": url, "safety": UNKNOWN_SAFETY, "record": provider_record_id},
        )
        asset_id = asset[0].id
        link = await fetch(
            session,
            """
            INSERT INTO entity_media
              (purpose, sort_order, entity_id, asset_id, observation_id)
            VALUES (:purpose, 0, :entity, :asset, :observation)
            ON CONFLICT DO NOTHING
            RETURNING id
            """,
            {
                "purpose": purpose,
                "entity": entity_id,
                "asset": asset_id,
                "observation": observation_id,
            },
        )
        written += len(link)
    return written


async def ensure_membership(session: AsyncSession, *, entity_id: Any, work_type: str) -> bool:
    """List anime and galgame works in their catalogue collection."""
    if work_type not in {"anime", "galgame"}:
        return False
    collection = await fetch(
        session,
        """
        INSERT INTO curated_collection (slug, name, is_enabled, created_at, updated_at)
        VALUES (:slug, :name, true, now(), now())
        ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name
        RETURNING id
        """,
        {"slug": work_type, "name": work_type.capitalize()},
    )
    await fetch(
        session,
        """
        INSERT INTO curated_membership
          (listing_state, inclusion_reason, collection_id, entity_id,
           created_at, updated_at)
        VALUES (:state, 'mapped work type', :collection, :entity, now(), now())
        ON CONFLICT (collection_id, entity_id) DO UPDATE
          SET listing_state = EXCLUDED.listing_state, updated_at = now()
        RETURNING id
        """,
        {
            "state": LISTED,
            "collection": collection[0].id,
            "entity": entity_id,
        },
    )
    return True


__all__ = [
    "LISTED",
    "ORIGINAL",
    "TRANSLATED",
    "UNKNOWN_SAFETY",
    "ensure_membership",
    "replace_names",
    "upsert_description",
    "upsert_media",
]
