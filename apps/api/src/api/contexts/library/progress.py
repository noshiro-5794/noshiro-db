"""Finished episodes belonging to a user's library entry."""

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.identity.resolution import cluster_ids, resolve
from api.contexts.presentation.detail import entity_detail
from api.contexts.presentation.episodes import episode_ids
from api.contexts.presentation.fragments import fetch
from api.contexts.presentation.summary import preferred_name


async def _entry(session: AsyncSession, *, user_id: int, entry_id: int, lock: bool = False) -> Any:
    rows = await fetch(
        session,
        "SELECT id,entity_id FROM user_library_entry"
        " WHERE id=:entry AND user_id=:user AND entity_id IS NOT NULL"
        + (" FOR UPDATE" if lock else ""),
        {"entry": entry_id, "user": user_id},
    )
    if not rows:
        raise LookupError(entry_id)
    return rows[0]


async def _episodes(session: AsyncSession, entity: UUID) -> tuple[UUID, list[UUID]]:
    root = await resolve(session, entity) or entity
    cluster = await cluster_ids(session, root)
    available = await episode_ids(session, [str(value) for value in cluster], public_only=False)
    return root, sorted(available)


async def _payload(session: AsyncSession, entry: Any) -> dict[str, Any]:
    root, available = await _episodes(session, entry.entity_id)
    stored = await fetch(
        session,
        "SELECT episode_entity_id FROM user_episode_progress"
        " WHERE user_subject_id=:entry AND is_finished",
        {"entry": entry.id},
    )
    finished = {row.episode_entity_id for row in stored}
    items = []
    for identifier in available:
        episode_root = await resolve(session, identifier) or identifier
        cluster = await cluster_ids(session, episode_root)
        detail = await entity_detail(
            session, root=episode_root, cluster_ids=[str(value) for value in cluster], language=""
        )
        facts: dict[str, Any] = {}
        for fact in detail["facts"]:
            facts.setdefault(fact["predicate"], fact["value"])
        items.append(
            {
                "id": str(identifier),
                "title": await preferred_name(session, entity_id=identifier, language=""),
                "title_cn": await preferred_name(session, entity_id=identifier, language="zh-Hans"),
                "type": facts.get("episode-type", ""),
                "number": facts.get("episode-number"),
                "sort": facts.get("sort"),
                "air_date": facts.get("air-date"),
                "is_finished": identifier in finished,
            }
        )
    return {
        "library_entry_id": entry.id,
        "entity_id": str(root),
        "total_episodes": len(items),
        "finished_count": len(finished),
        "finished_episode_ids": [item["id"] for item in items if item["is_finished"]],
        "episodes": items,
    }


async def get_progress(session: AsyncSession, *, user_id: int, entry_id: int) -> dict[str, Any]:
    return await _payload(session, await _entry(session, user_id=user_id, entry_id=entry_id))


async def replace_progress(
    session: AsyncSession, *, user_id: int, entry_id: int, finished: list[UUID]
) -> dict[str, Any]:
    entry = await _entry(session, user_id=user_id, entry_id=entry_id, lock=True)
    _, available = await _episodes(session, entry.entity_id)
    if not set(finished).issubset(available):
        raise ValueError({"finished_episode_ids": "Contains an episode outside this Work."})
    await fetch(
        session,
        "DELETE FROM user_episode_progress WHERE user_subject_id=:entry RETURNING id",
        {"entry": entry.id},
    )
    await fetch(
        session,
        "INSERT INTO user_episode_progress(user_subject_id,episode_entity_id,is_finished)"
        " SELECT :entry,episode,true FROM unnest(CAST(:episodes AS uuid[])) AS episode"
        " RETURNING id",
        {"entry": entry.id, "episodes": [str(value) for value in finished]},
    )
    await session.commit()
    return await _payload(session, entry)


async def set_finished(
    session: AsyncSession, *, user_id: int, entry_id: int, episode_id: UUID
) -> dict[str, Any]:
    entry = await _entry(session, user_id=user_id, entry_id=entry_id, lock=True)
    _, available = await _episodes(session, entry.entity_id)
    if episode_id not in available:
        raise FileNotFoundError(episode_id)
    await fetch(
        session,
        "INSERT INTO user_episode_progress(user_subject_id,episode_entity_id,is_finished)"
        " VALUES (:entry,:episode,true) ON CONFLICT (user_subject_id,episode_entity_id)"
        " DO UPDATE SET is_finished=true RETURNING id",
        {"entry": entry.id, "episode": episode_id},
    )
    await session.commit()
    return await _payload(session, entry)


async def clear_finished(
    session: AsyncSession, *, user_id: int, entry_id: int, episode_id: UUID
) -> None:
    entry = await _entry(session, user_id=user_id, entry_id=entry_id, lock=True)
    await fetch(
        session,
        "DELETE FROM user_episode_progress WHERE user_subject_id=:entry"
        " AND episode_entity_id=:episode"
        " RETURNING id",
        {"entry": entry.id, "episode": episode_id},
    )
    await session.commit()
