"""Persistence and lookup for captured provider responses."""

from hashlib import sha256
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from api.db import fetch
from api.integrations.providers.capture import SourceResponse


async def store(session: AsyncSession, response: SourceResponse) -> UUID:
    params = {
        "provider": response.provider,
        "hash": sha256(response.body).hexdigest(),
        "body": response.body,
    }
    rows = await fetch(
        session,
        """
        INSERT INTO ingest.source_document (provider_id, body_hash, body)
        SELECT id, :hash, :body FROM provider
        WHERE slug = :provider AND is_enabled AND storage_policy = 'allowed'
        ON CONFLICT (provider_id, body_hash) DO NOTHING RETURNING id
        """,
        params,
    )
    if not rows:
        rows = await fetch(
            session,
            """
            SELECT document.id FROM ingest.source_document AS document
            JOIN provider ON provider.id = document.provider_id
            WHERE provider.slug = :provider AND provider.is_enabled
              AND provider.storage_policy = 'allowed' AND document.body_hash = :hash
            """,
            {"provider": response.provider, "hash": params["hash"]},
        )
    if not rows:
        raise PermissionError(f"Raw response storage is not permitted for {response.provider}.")
    await fetch(
        session,
        """
        INSERT INTO ingest.source_fetch (
            id, document_id, endpoint, method, status_code, content_type, fetched_at
        ) VALUES (:id, :document, :endpoint, :method, :status, :type, :at)
        RETURNING id
        """,
        {
            "id": response.id,
            "document": rows[0].id,
            "endpoint": response.endpoint,
            "method": response.method,
            "status": response.status_code,
            "type": response.content_type,
            "at": response.fetched_at,
        },
    )
    return response.id


async def link_revision(
    session: AsyncSession, *, revision_id: UUID, fetch_id: UUID, pointer: str = ""
) -> None:
    rows = await fetch(
        session,
        """
        INSERT INTO ingest.revision_source (revision_id, fetch_id, json_pointer)
        SELECT revision.id, source.id, :pointer
        FROM provider_revision AS revision
        JOIN provider_record AS record ON record.id = revision.record_id
        JOIN provider_namespace AS namespace ON namespace.id = record.namespace_id
        JOIN ingest.source_fetch AS source ON source.id = :fetch
        JOIN ingest.source_document AS document ON document.id = source.document_id
          AND document.provider_id = namespace.provider_id
        WHERE revision.id = :revision
        ON CONFLICT DO NOTHING RETURNING revision_id
        """,
        {"revision": revision_id, "fetch": fetch_id, "pointer": pointer},
    )
    if rows:
        return
    existing = await fetch(
        session,
        """
        SELECT revision_id FROM ingest.revision_source
        WHERE revision_id = :revision AND fetch_id = :fetch AND json_pointer = :pointer
        """,
        {"revision": revision_id, "fetch": fetch_id, "pointer": pointer},
    )
    if not existing:
        raise ValueError("The fetch and revision must belong to the same provider.")


async def body_for_fetch(
    session: AsyncSession, fetch_id: UUID, *, provider: str, endpoint: str
) -> bytes:
    rows = await fetch(
        session,
        """
        SELECT document.body FROM ingest.source_fetch AS source
        JOIN ingest.source_document AS document ON document.id = source.document_id
        JOIN provider ON provider.id = document.provider_id
        WHERE source.id = :id AND source.endpoint = :endpoint AND provider.slug = :provider
          AND provider.is_enabled AND provider.storage_policy = 'allowed'
        """,
        {"id": fetch_id, "endpoint": endpoint, "provider": provider},
    )
    if not rows:
        raise LookupError("Source response is unavailable.")
    return bytes(rows[0].body)
