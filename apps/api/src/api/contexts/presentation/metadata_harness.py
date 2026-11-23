"""Evidence and draft commands shared by the metadata harness and its tools."""

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import settings
from api.contexts.identity.resolution import cluster_ids, is_active, is_public, resolve
from api.contexts.knowledge import agent_runs
from api.contexts.knowledge.agent_runs import WriteGuard
from api.db import fetch
from api.shared.inference import fail_run, start_run, store_result
from api.worker.session import session_scope

from .agent import propose_with_model
from .bundle import build_bundle
from .display import DisplayProposal, submit, validate


class MetadataDraft(BaseModel):
    entity_id: UUID
    language: str = Field(max_length=35)
    input_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    title_name_id: int = Field(gt=0)
    description: str = Field(default="", max_length=2000)
    description_source_ids: list[int] = Field(default_factory=list, max_length=3)
    cover_asset_id: UUID | None = None


async def evidence(session: AsyncSession, *, entity_id: UUID, language: str) -> dict[str, Any]:
    root = await resolve(session, entity_id)
    if root is None or not await is_active(session, root):
        raise LookupError("Active public work not found.")
    members = await cluster_ids(session, root)
    if not await is_public(session, members):
        raise LookupError("Active public work not found.")
    return await build_bundle(
        session,
        root=root,
        cluster_ids=sorted(map(str, members)),
        language=language,
        for_ai=True,
    )


async def submit_draft(session: AsyncSession, value: MetadataDraft) -> dict[str, Any]:
    current = await evidence(session, entity_id=value.entity_id, language=value.language)
    if current["input_hash"] != value.input_hash:
        raise ValueError("Work evidence has changed. Read it again before submitting a draft.")
    bundle = current["bundle"]
    proposal = DisplayProposal(
        title_name_id=value.title_name_id,
        description_text=value.description,
        description_source_ids=value.description_source_ids,
        cover_asset_id=str(value.cover_asset_id) if value.cover_asset_id else None,
        is_machine_generated=True,
    )
    identifier, state = await submit(
        session,
        bundle=bundle,
        proposal=proposal,
        input_hash=value.input_hash,
        model="",
        prompt_version="metadata-mcp-v1",
    )
    return {"id": identifier, "state": state}


async def generate(
    *, entity_id: UUID, language: str, run_id: UUID, before_write: WriteGuard
) -> Literal["drafts", "skipped", "abstained"]:
    """Generate one work draft and keep model audit separate from publication."""
    async with session_scope() as session:
        current = await evidence(session, entity_id=entity_id, language=language)
        bundle = current["bundle"]
        if not bundle["names"]:
            return "abstained"
        fingerprint = current["input_hash"]
        previous = await fetch(
            session,
            """
            SELECT id FROM entity_metadata_revision
            WHERE entity_id=CAST(:id AS uuid) AND language=:language AND input_hash=:hash
              AND state IN ('draft','approved')
            """,
            {"id": bundle["entity"]["id"], "language": language, "hash": fingerprint},
        )
        if previous:
            return "skipped"
        context = {
            "entity_id": bundle["entity"]["id"],
            "language": language,
            "input_hash": fingerprint,
        }
        step_id = await agent_runs.create_step(
            session, run_id=run_id, skill="metadata_draft", payload=context
        )
    inference = await start_run(
        payload=context,
        use_case="metadata_draft",
        prompt_version="metadata-v1",
        metadata=context,
        agent_step_id=step_id,
    )
    try:
        proposal, usage = await propose_with_model(bundle)
        if errors := validate(bundle, proposal, language=language):
            raise ValueError(" ".join(errors))
    except Exception as error:
        await fail_run(inference, error)
        async with session_scope() as session:
            await agent_runs.finish_step(session, step_id, None, error=str(error))
        return "abstained"

    try:
        async with session_scope() as session:
            await before_write(session)
            checked = await evidence(session, entity_id=entity_id, language=language)
            if checked["input_hash"] != fingerprint:
                raise ValueError("Work evidence changed during inference.")
            draft_id, state = await submit(
                session,
                bundle=checked["bundle"],
                proposal=proposal,
                input_hash=fingerprint,
                model=settings.ai_model,
                prompt_version="metadata-v1",
                agent_step_id=step_id,
            )
            result = {"draft_id": draft_id, "state": state}
            await store_result(session, inference, result, usage)
            await agent_runs.finish_step(session, step_id, result)
        return "drafts"
    except Exception as error:
        await fail_run(inference, error)
        async with session_scope() as session:
            await agent_runs.finish_step(session, step_id, None, error=str(error))
        raise
