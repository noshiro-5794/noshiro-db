"""Fetching and atomically projecting a complete manual Bangumi subject sync."""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.presentation.summary import preferred_name
from api.db import fetch
from api.integrations.providers.bangumi import BangumiClient
from api.worker.bangumi_entities import import_entity
from api.worker.bangumi_episodes import import_episodes
from api.worker.bangumi_relations import RelatedIds, import_relations, related_ids
from api.worker.subject_import import import_subject


@dataclass(frozen=True, slots=True)
class SubjectBatch:
    subject: dict[str, Any]
    episodes: list[Any]
    subjects: list[Any]
    staff: list[Any]
    characters: list[Any]
    people_details: dict[str, dict[str, Any]]
    character_details: dict[str, dict[str, Any]]


async def fetch_batch(
    client: BangumiClient,
    subject_id: int,
    *,
    progress: Callable[[str, int | None], Awaitable[None]],
) -> SubjectBatch:
    subject = await asyncio.to_thread(client.fetch_subject, subject_id)
    await progress(f"Fetched subject {subject_id}", None)
    episodes = []
    offset = 0
    while True:
        page = await asyncio.to_thread(
            client.fetch_subject_episodes, subject_id=subject_id, limit=100, offset=offset
        )
        episodes.extend(page["data"])
        await progress(f"Fetched episodes for {subject_id}", None)
        if len(page["data"]) < 100:
            break
        offset += 100
    subjects = await asyncio.to_thread(client.fetch_subject_subjects, subject_id)
    staff = await asyncio.to_thread(client.fetch_subject_persons, subject_id)
    characters = await asyncio.to_thread(client.fetch_subject_characters, subject_id)
    identifiers = related_ids(subjects, staff, characters)
    total = 3 + len(identifiers.staff) + len(identifiers.characters)
    await progress(f"Fetched relations for {subject_id}", total)
    character_details = {}
    for identifier in sorted(identifiers.characters, key=int):
        character_details[identifier] = await asyncio.to_thread(
            client.fetch_character, int(identifier)
        )
        await progress(f"Fetched character {identifier}", total)
    people_details = {}
    for identifier in sorted(identifiers.staff, key=int):
        people_details[identifier] = await asyncio.to_thread(client.fetch_person, int(identifier))
        await progress(f"Fetched staff {identifier}", total)
    return SubjectBatch(
        subject, episodes, subjects, staff, characters, people_details, character_details
    )


async def project_batch(
    session: AsyncSession, subject_id: int, batch: SubjectBatch
) -> dict[str, Any]:
    async with session.begin_nested():
        work_id = await import_subject(session, batch.subject)
        await import_episodes(session, work_id, str(subject_id), batch.episodes)
        identifiers: RelatedIds = await import_relations(
            session,
            work_id,
            str(subject_id),
            subjects=batch.subjects,
            staff=batch.staff,
            characters=batch.characters,
        )
        for identifier in sorted(identifiers.characters, key=int):
            await import_entity(session, batch.character_details[identifier], "character")
        for identifier in sorted(identifiers.staff, key=int):
            await import_entity(session, batch.people_details[identifier], "person")
        work = (
            await fetch(session, "SELECT work_type FROM work WHERE entity_id=:id", {"id": work_id})
        )[0]
        return {
            "subject_id": str(work_id),
            "bangumi_id": subject_id,
            "title": await preferred_name(session, entity_id=work_id, language=""),
            "subject_type": work.work_type,
            "episode_synced": True,
            "staff_count": len(identifiers.staff),
            "character_count": len(identifiers.characters),
            "related_subject_count": len(identifiers.subjects),
        }
