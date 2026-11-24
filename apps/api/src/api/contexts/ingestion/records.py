"""Turning a fetched provider payload into a record and a revision.

Ported from `ProviderRecordService.record_many`. The guarantees that matter:

* One record per ``(namespace, external_id)``, created on demand and then locked.
* A revision only when the payload **actually changed** — compared by a canonical hash,
  so a re-fetch that returns the same body costs one read and no row.
* The record points to one current revision. The revision itself owns the payload hash.

``raw_state`` records how complete the stored payload is, per provider and namespace: a
calendar page is a bounded projection, a Bangumi record without payload is legacy.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.ingestion import archive
from api.db import fetch
from api.integrations.providers.capture import origins

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
_preserve_current = ContextVar("preserve_current_revisions", default=False)


@contextmanager
def preserve_current_revisions() -> Iterator[None]:
    token = _preserve_current.set(True)
    try:
        yield
    finally:
        _preserve_current.reset(token)


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
        ON CONFLICT (provider_id, slug) DO UPDATE SET slug = EXCLUDED.slug
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


async def ensure_record(
    session: AsyncSession,
    *,
    provider_slug: str,
    namespace_slug: str,
    resource_type: str,
    external_id: str,
    canonical_url: str = "",
    origin: str = "api",
) -> Any:
    """Refresh an embedded reference without replacing a fetched payload or revision."""
    identifier = external_id.strip()
    if not identifier:
        raise ValueError("Source external_id must not be empty.")
    namespace_id = await ensure_namespace(
        session,
        provider_slug=provider_slug,
        namespace_slug=namespace_slug,
        resource_type=resource_type,
    )
    rows = await fetch(
        session,
        """
        INSERT INTO provider_record
          (id, namespace_id, external_id, canonical_url, status, origin, raw_state,
           latest_revision_id,
           first_seen_at, last_seen_at, created_at, updated_at)
        VALUES (gen_random_uuid(), :namespace, :external_id, :url, 'active', :origin,
                :raw_state, NULL, clock_timestamp(), clock_timestamp(), now(), now())
        ON CONFLICT (namespace_id, external_id) DO UPDATE
        SET canonical_url = CASE WHEN EXCLUDED.canonical_url = ''
                                 THEN provider_record.canonical_url ELSE EXCLUDED.canonical_url END,
            status = 'active', origin = EXCLUDED.origin,
            last_seen_at = clock_timestamp(), updated_at = now()
        RETURNING id
        """,
        {
            "namespace": namespace_id,
            "external_id": identifier,
            "url": canonical_url,
            "origin": origin,
            "raw_state": stub_state_for_namespace(provider_slug=provider_slug),
        },
    )
    return rows[0].id


async def lock_work_import(session: AsyncSession, provider: str, external_id: str) -> None:
    await fetch(
        session,
        "SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))",
        {"key": f"work-import:{provider}:{external_id}"},
    )


async def detailed_work_entity(
    session: AsyncSession, provider: str, external_id: str, mapper_version: str
) -> Any:
    rows = await fetch(
        session,
        """
        SELECT representation.entity_id
        FROM provider_record AS record
        JOIN provider_namespace AS namespace ON namespace.id = record.namespace_id
        JOIN provider ON provider.id = namespace.provider_id
        JOIN entity_representation AS representation
          ON representation.provider_record_id = record.id
          AND representation.is_active
        JOIN provider_revision AS revision ON revision.id = record.latest_revision_id
        WHERE provider.slug = :provider AND namespace.slug = 'anime' AND record.external_id = :id
          AND record.status = 'active' AND (
              revision.payload ? 'genres' OR EXISTS (
                  SELECT 1 FROM mapping_run WHERE revision_id = revision.id
                    AND mapper_version = :version AND status = 'succeeded'
              )
          )
        ORDER BY representation.id LIMIT 1
        """,
        {"provider": provider, "id": external_id, "version": mapper_version},
    )
    return rows[0].entity_id if rows else None


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
    upstream_updated_at: datetime | None = None,
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
           latest_revision_id,
           first_seen_at, last_seen_at, created_at, updated_at)
        VALUES (gen_random_uuid(), :namespace, :external_id, :url, 'active', :origin,
                :raw_state, NULL, :at, :at, now(), now())
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
        """
        SELECT record.id, revision.payload_hash, record.status
        FROM provider_record AS record
        LEFT JOIN provider_revision AS revision ON revision.id = record.latest_revision_id
        WHERE record.namespace_id = :namespace AND record.external_id = :external_id
        FOR UPDATE OF record
        """,
        {"namespace": namespace_id, "external_id": external_id},
    )
    if not rows:
        raise RecordConflict(f"Record {namespace_slug}:{external_id} could not be persisted.")
    record_id = rows[0].id
    digest = payload_hash(payload)
    changed = rows[0].payload_hash != digest
    if _preserve_current.get() and (
        rows[0].status != "active" or (changed and rows[0].payload_hash)
    ):
        raise RecordConflict(f"Replay would override {namespace_slug}:{external_id}.")

    if changed:
        await fetch(
            session,
            """
            INSERT INTO provider_revision
              (id, record_id, payload, payload_hash, schema_version, response_metadata,
               upstream_updated_at, fetched_at)
            VALUES (gen_random_uuid(), :record, CAST(:payload AS jsonb), :hash,
                    :schema_version, '{}'::jsonb, :upstream_updated_at, :at)
            ON CONFLICT DO NOTHING
            RETURNING id
            """,
            {
                "record": record_id,
                "payload": json.dumps(payload, ensure_ascii=False),
                "hash": digest,
                "schema_version": schema_version,
                "upstream_updated_at": upstream_updated_at,
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
    for source in origins(payload):
        await archive.link_revision(
            session,
            revision_id=revision_id,
            fetch_id=source.fetch_id,
            pointer=source.pointer,
        )
    await fetch(
        session,
        """
        UPDATE provider_record
        SET canonical_url = CASE WHEN :url = '' THEN canonical_url ELSE :url END,
            status = 'active', origin = :origin, raw_state = :raw_state,
            last_seen_at = :at,
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
