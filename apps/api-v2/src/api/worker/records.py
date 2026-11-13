"""Turning a fetched provider payload into a record and a revision.

Ported from `ProviderRecordService.record_many`. The guarantees that matter:

* One record per ``(namespace, external_id)``, created on demand and then locked.
* A revision only when the payload **actually changed** — compared by a canonical hash,
  so a re-fetch that returns the same body costs one read and no row.
* The record always points at the revision matching ``latest_payload_hash``; a record whose
  revision cannot be found is a conflict, not something to paper over.

``raw_state`` records how complete the stored payload is, per provider and namespace: a
calendar page is a bounded projection, a Bangumi record without payload is legacy.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.presentation.fragments import fetch

SLIM_NAMESPACES = frozenset(
    {
        ("anilist", "anime"),
        ("anilist", "episode"),
        ("anilist", "season-item"),
        ("anilist", "calendar"),
        ("anilist", "season"),
        ("mal", "schedule-item"),
        ("mal", "season"),
        ("bangumi", "calendar"),
        ("vndb", "vn-related"),
    }
)

RAW = "raw"
SLIM = "slim"
STUB = "stub"
LEGACY = "legacy"


class RecordConflict(RuntimeError):
    """The catalogue could not be kept consistent with the payload."""


@dataclass(frozen=True)
class RecordWrite:
    record_id: Any
    revision_id: Any
    changed: bool


def raw_state_for_namespace(*, provider_slug: str, namespace_slug: str) -> str:
    return SLIM if (provider_slug, namespace_slug) in SLIM_NAMESPACES else RAW


def stub_state_for_namespace(*, provider_slug: str) -> str:
    return LEGACY if provider_slug == "bangumi" else STUB


def payload_hash(payload: dict[str, Any]) -> str:
    """Canonical digest of a provider payload; order and whitespace are irrelevant."""
    serialized = json.dumps(
        payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode()
    return hashlib.sha256(serialized).hexdigest()


async def ensure_namespace(
    session: AsyncSession, *, provider_slug: str, namespace_slug: str, resource_type: str
) -> Any:
    rows = await fetch(
        session,
        """
        SELECT ns.id
        FROM provider_namespace AS ns
        JOIN provider AS p ON p.id = ns.provider_id
        WHERE p.slug = :provider AND ns.slug = :namespace
        """,
        {"provider": provider_slug, "namespace": namespace_slug},
    )
    if rows:
        return rows[0].id
    created = await fetch(
        session,
        """
        INSERT INTO provider_namespace
          (slug, resource_type, description, provider_id, created_at, updated_at)
        SELECT :namespace, :resource_type, '', p.id, now(), now()
        FROM provider AS p WHERE p.slug = :provider
        RETURNING id
        """,
        {
            "namespace": namespace_slug,
            "resource_type": resource_type,
            "provider": provider_slug,
        },
    )
    if not created:
        raise RecordConflict(f"Provider {provider_slug} is not registered.")
    return created[0].id


async def record_payload(
    session: AsyncSession,
    *,
    provider_slug: str,
    namespace_slug: str,
    resource_type: str,
    external_id: str,
    payload: dict[str, Any],
    schema_version: str = "",
    canonical_url: str = "",
    origin: str = "api",
    fetched_at: datetime | None = None,
) -> RecordWrite:
    """Store the payload and return the record, the revision, and whether it changed."""
    if not external_id.strip():
        raise ValueError("Source external_id must not be empty.")
    at = fetched_at or datetime.now(UTC)
    namespace_id = await ensure_namespace(
        session,
        provider_slug=provider_slug,
        namespace_slug=namespace_slug,
        resource_type=resource_type,
    )
    await fetch(
        session,
        """
        INSERT INTO provider_record
          (id, namespace_id, external_id, canonical_url, status, origin, raw_state,
           latest_payload_hash, latest_revision_id,
           first_seen_at, last_seen_at, created_at, updated_at)
        VALUES (gen_random_uuid(), :namespace, :external_id, :url, 'active', :origin,
                :raw_state, '', NULL, :at, :at, now(), now())
        ON CONFLICT (namespace_id, external_id) DO NOTHING
        RETURNING id
        """,
        {
            "namespace": namespace_id,
            "external_id": external_id,
            "url": canonical_url,
            "origin": origin,
            "raw_state": stub_state_for_namespace(provider_slug=provider_slug),
            "at": at,
        },
    )
    rows = await fetch(
        session,
        "SELECT id, latest_payload_hash FROM provider_record"
        " WHERE namespace_id = :namespace AND external_id = :external_id FOR UPDATE",
        {"namespace": namespace_id, "external_id": external_id},
    )
    if not rows:
        raise RecordConflict(f"Record {namespace_slug}:{external_id} could not be persisted.")
    record_id = rows[0].id
    digest = payload_hash(payload)
    changed = rows[0].latest_payload_hash != digest

    if changed:
        await fetch(
            session,
            """
            INSERT INTO provider_revision
              (id, record_id, payload, payload_hash, schema_version, response_metadata,
               upstream_updated_at, fetched_at)
            VALUES (gen_random_uuid(), :record, CAST(:payload AS jsonb), :hash,
                    :schema_version, '{}'::jsonb, NULL, :at)
            ON CONFLICT DO NOTHING
            RETURNING id
            """,
            {
                "record": record_id,
                "payload": json.dumps(payload, ensure_ascii=False),
                "hash": digest,
                "schema_version": schema_version,
                "at": at,
            },
        )

    revision = await fetch(
        session,
        "SELECT id FROM provider_revision WHERE record_id = :record"
        " AND payload_hash = :hash ORDER BY fetched_at DESC LIMIT 1",
        {"record": record_id, "hash": digest},
    )
    if not revision:
        raise RecordConflict(f"Revision missing for {namespace_slug}:{external_id}.")
    revision_id = revision[0].id
    await fetch(
        session,
        """
        UPDATE provider_record
        SET canonical_url = CASE WHEN :url = '' THEN canonical_url ELSE :url END,
            status = 'active', origin = :origin, raw_state = :raw_state,
            last_seen_at = :at, latest_payload_hash = :hash,
            latest_revision_id = :revision, updated_at = now()
        WHERE id = :record
        RETURNING id
        """,
        {
            "url": canonical_url,
            "origin": origin,
            "raw_state": raw_state_for_namespace(
                provider_slug=provider_slug, namespace_slug=namespace_slug
            ),
            "at": at,
            "hash": digest,
            "revision": revision_id,
            "record": record_id,
        },
    )
    return RecordWrite(record_id=record_id, revision_id=revision_id, changed=changed)


__all__ = [
    "LEGACY",
    "RAW",
    "SLIM",
    "STUB",
    "RecordConflict",
    "RecordWrite",
    "ensure_namespace",
    "payload_hash",
    "raw_state_for_namespace",
    "record_payload",
    "stub_state_for_namespace",
]
