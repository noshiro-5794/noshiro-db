from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .domain import MetricRow


async def list_metrics(session: AsyncSession, entity_ids: set[UUID]) -> list[MetricRow]:
    rows = (
        await session.execute(
            text(
                """
                SELECT snapshot.metric,
                       snapshot.value,
                       snapshot.sample_size,
                       snapshot.observed_at,
                       provider.slug AS provider
                FROM metric_snapshot AS snapshot
                JOIN provider_record AS record ON record.id = snapshot.provider_record_id
                JOIN provider_namespace AS namespace ON namespace.id = record.namespace_id
                JOIN provider AS provider ON provider.id = namespace.provider_id
                WHERE snapshot.entity_id = ANY(CAST(:entity_ids AS uuid[]))
                  AND provider.redistribution_policy <> 'forbidden'
                ORDER BY snapshot.metric, snapshot.observed_at DESC
                """
            ),
            {"entity_ids": [str(value) for value in entity_ids]},
        )
    ).all()
    return [
        MetricRow(
            metric=row.metric,
            value=row.value,
            sample_size=row.sample_size,
            observed_at=row.observed_at,
            provider=row.provider,
        )
        for row in rows
    ]
