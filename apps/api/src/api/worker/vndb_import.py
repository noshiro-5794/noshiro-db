"""Atomic VNDB import with source graph projection and explicit-ID reconciliation."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.identity import vndb as identity
from api.integrations.providers.vndb import VNDBImportBatch
from api.worker import vndb_graph as graph
from api.worker import vndb_related as related
from api.worker.vndb_projection import Projection, project_work, record_source


async def project_batch(session: AsyncSession, vndb_id: str, batch: VNDBImportBatch) -> Projection:
    """Persist the complete source graph together, rolling back a failed projection."""
    if not vndb_id.startswith("v"):
        raise ValueError("VNDB work IDs must start with 'v'.")
    async with session.begin_nested():
        work = await project_work(session, vndb_id, batch.work)
        await graph.import_credits(session, work, batch.work)
        await graph.import_relations(session, work, batch.work)
        if batch.related_fetched:
            _, observation_id = await record_source(
                session,
                {
                    "releases": batch.releases,
                    "characters": batch.characters,
                    "contributors": batch.contributors,
                },
                namespace="vn-related",
                resource_type="collection",
                mapper="vndb.vn.related",
                mapper_version="vndb-vn-related-v1",
                schema_name="index.work.related",
                external_id=vndb_id,
            )
            await related.import_releases(
                session, work.entity_id, vndb_id, observation_id, batch.releases
            )
            await related.import_characters(
                session, work.entity_id, vndb_id, observation_id, batch.characters
            )
            await graph.import_staff(session, batch.contributors)
        await graph.import_voices(session, work, batch.work)
        return work


async def import_batch(session: AsyncSession, vndb_id: str, batch: VNDBImportBatch) -> Any:
    """Project and reconcile as one transaction owned by the caller."""
    async with session.begin_nested():
        work = await project_batch(session, vndb_id, batch)
        return await identity.reconcile(session, work.entity_id, vndb_id)
