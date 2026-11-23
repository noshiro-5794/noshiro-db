"""Reconstruct an import using the catalogue's recorded responses."""

from collections.abc import Mapping
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.ingestion.records import preserve_current_revisions
from api.db import fetch
from api.integrations.providers.capture import REPLAY_FETCH_ID, request_hash
from api.worker.campaign_imports import load_source, project_source

BASE_PATHS = {"bangumi": "/", "anilist": "/", "mal": "/v2/", "vndb": "/kana/"}


async def replay_batch(session: AsyncSession, batch_id: UUID, *, apply: bool) -> Any:
    rows = await fetch(
        session,
        """
        SELECT provider.slug, batch.external_id
        FROM ingest.source_batch AS batch JOIN provider ON provider.id = batch.provider_id
        WHERE batch.id = :id AND batch.completed_at IS NOT NULL
          AND provider.is_enabled AND provider.storage_policy = 'allowed'
        """,
        {"id": batch_id},
    )
    if not rows:
        raise LookupError("The captured batch is incomplete or unavailable.")
    batch = rows[0]
    responses = await fetch(
        session,
        """
        SELECT DISTINCT ON (source.request_hash)
               source.id, source.request_hash, source.status_code, source.content_type,
               document.body
        FROM ingest.source_fetch AS source
        JOIN ingest.source_document AS document ON document.id = source.document_id
        JOIN ingest.source_batch AS batch ON batch.id = source.batch_id
          AND batch.provider_id = document.provider_id
        WHERE batch.id = :id
        ORDER BY source.request_hash, source.fetched_at DESC, source.id DESC
        """,
        {"id": batch_id},
    )
    recorded = {row.request_hash: row._mapping for row in responses}

    def receive(request: httpx.Request) -> httpx.Response:
        response: Mapping[str, Any] | None = recorded.get(request_hash(request))
        if response is None:
            raise LookupError(f"Captured batch lacks a response for {request.url.path}.")
        return httpx.Response(
            response["status_code"],
            content=bytes(response["body"]),
            headers={"Content-Type": response["content_type"]},
            extensions={REPLAY_FETCH_ID: response["id"]},
        )

    async def ignore_progress(_message: str, _total: int | None) -> None:
        pass

    http = httpx.Client(
        base_url="https://source-replay.invalid" + BASE_PATHS[batch.slug],
        transport=httpx.MockTransport(receive),
        trust_env=False,
    )
    with http:
        payload = await load_source(
            batch.slug,
            batch.external_id,
            forbidden=False,
            progress=ignore_progress,
            http=http,
        )
    async with session.begin_nested() as projection:
        if apply:
            await require_current_batch(session, batch_id)
            with preserve_current_revisions():
                result = await project_source(session, batch.slug, batch.external_id, payload)
        else:
            result = await project_source(session, batch.slug, batch.external_id, payload)
            await projection.rollback()
    return result


async def require_current_batch(session: AsyncSession, batch_id: UUID) -> None:
    rows = await fetch(
        session,
        """
        SELECT record.id, record.status, record.latest_revision_id IN (
            SELECT link.revision_id FROM ingest.revision_source AS link
            JOIN ingest.source_fetch AS captured ON captured.id = link.fetch_id
            WHERE captured.batch_id = :batch
        ) AS current
        FROM provider_record AS record
        WHERE record.id IN (
            SELECT revision.record_id FROM ingest.revision_source AS link
            JOIN ingest.source_fetch AS captured ON captured.id = link.fetch_id
            JOIN provider_revision AS revision ON revision.id = link.revision_id
            WHERE captured.batch_id = :batch
        )
        ORDER BY record.id
        FOR UPDATE OF record
        """,
        {"batch": batch_id},
    )
    if not rows or any(row.status != "active" or not row.current for row in rows):
        raise ValueError("Only a batch that matches the current source revisions can be applied.")
    later = await fetch(
        session,
        """
        SELECT 1 FROM ingest.source_batch AS original
        JOIN ingest.source_batch AS later
          ON later.provider_id = original.provider_id AND later.external_id = original.external_id
        WHERE original.id = :batch AND later.started_at > original.started_at
          AND later.completed_at IS NOT NULL
        LIMIT 1
        """,
        {"batch": batch_id},
    )
    if later:
        raise ValueError("A newer capture is available for this source work.")
