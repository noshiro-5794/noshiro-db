"""The provenance list: which records back an entity, and at which revision."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from .fragments import fetch, isoformat


async def entity_evidence(session: AsyncSession, *, cluster: list[str]) -> list[dict[str, Any]]:
    rows = await fetch(
        session,
        """
        SELECT provider.slug AS provider,
               namespace.slug AS namespace,
               record.external_id AS external_id,
               record.latest_revision_id AS revision_id,
               representation.created_at AS observed_at
        FROM entity_representation AS representation
        JOIN provider_record AS record ON record.id = representation.provider_record_id
        JOIN provider_namespace AS namespace ON namespace.id = record.namespace_id
        JOIN provider AS provider ON provider.id = namespace.provider_id
        WHERE representation.entity_id = ANY(CAST(:ids AS uuid[]))
          AND representation.is_active
          AND provider.redistribution_policy <> 'forbidden'
        ORDER BY representation.id
        """,
        {"ids": cluster},
    )
    return [
        {
            "provider": row.provider,
            "namespace": row.namespace,
            "external_id": row.external_id,
            "revision_id": str(row.revision_id) if row.revision_id else None,
            "observed_at": isoformat(row.observed_at),
        }
        for row in rows
    ]
