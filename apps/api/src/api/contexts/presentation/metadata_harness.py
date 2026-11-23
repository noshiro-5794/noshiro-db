"""Evidence and draft commands shared by the metadata harness and its tools."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.identity.resolution import cluster_ids, is_active, is_public, resolve

from .bundle import build_bundle
from .display import DisplayProposal, submit
from .rules import propose


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
        field_choices=propose(bundle).field_choices,
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
