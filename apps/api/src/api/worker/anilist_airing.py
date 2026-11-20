"""AniList calendar observations, stable episode identities and airing events."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.ingestion import entities, facts, records
from api.contexts.ingestion import metadata as presentation
from api.contexts.ingestion import observations as ingestion
from api.contexts.ingestion import relations as graph
from api.db import fetch
from api.worker.anilist_import import as_int


async def import_schedule(session: AsyncSession, work_id: Any, media: dict[str, Any]) -> None:
    schedule = media.get("airingSchedule") or {}
    nodes = schedule.get("nodes") or []
    if not isinstance(nodes, list) or not nodes:
        next_episode = media.get("nextAiringEpisode") or {}
        airing_at = as_int(next_episode.get("airingAt"))
        if airing_at is None:
            return
        nodes = [{"episode": as_int(next_episode.get("episode")), "airingAt": airing_at}]
    payload = {"media": media, "schedule": nodes}
    calendar = await records.record_payload(
        session,
        provider_slug="anilist",
        namespace_slug="calendar",
        resource_type="schedule",
        external_id=str(media["id"]),
        payload=payload,
        schema_version="anilist-graphql",
        canonical_url=f"https://anilist.co/anime/{media['id']}",
    )
    observation_id = await ingestion.record_observation(
        session,
        provider_record_id=calendar.record_id,
        mapper="anilist.airing",
        mapper_version="anilist-airing-v2",
        normalized_data=payload,
        schema_name="index.schedule",
        schema_version="1",
    )
    for index, item in enumerate(nodes):
        if not isinstance(item, dict):
            continue
        airing_at = as_int(item.get("airingAt"))
        if airing_at is None:
            continue
        starts_at = datetime.fromtimestamp(airing_at, tz=UTC)
        episode = await upsert_episode(
            session, work_id, media, item, starts_at, observation_id, index
        )
        await fetch(
            session,
            """
            INSERT INTO airing_event
              (work_id, episode_entity_id, starts_at, timezone, region, weekday, precision,
               raw_value, observation_id, collection_doing, created_at, updated_at)
            VALUES (:work, :episode, :starts, 'UTC', '', :weekday, 'minute', :raw,
                    :observation, 0, now(), now()) ON CONFLICT DO NOTHING RETURNING id
            """,
            {
                "work": work_id,
                "episode": episode,
                "starts": starts_at,
                "weekday": starts_at.isoweekday(),
                "raw": starts_at.isoformat(),
                "observation": observation_id,
            },
        )
        number = as_int(item.get("episode"))
        if number is not None:
            for slug, name, value in (
                ("episode-number", "Episode Number", str(number)),
                ("episode-type", "Episode Type", "EP"),
            ):
                await facts.record_fact(
                    session,
                    entity_id=episode,
                    observation_id=observation_id,
                    slug=slug,
                    name=name,
                    value=value,
                    value_type="string",
                    json_pointer=f"/schedule/{index}/episode",
                )


async def upsert_episode(
    session: AsyncSession,
    work_id: Any,
    media: dict[str, Any],
    item: dict[str, Any],
    starts_at: datetime,
    calendar_observation: Any,
    index: int,
) -> Any:
    number = as_int(item.get("episode"))
    # The next-episode fallback has no globally unique schedule ID.
    external_id = str(
        item.get("id") or f"{media['id']}:{item.get('episode') or starts_at.isoformat()}"
    )
    stable: dict[str, Any] = {
        key: item[key] for key in ("id", "episode", "airingAt") if key in item
    }
    if not stable:
        stable = {"id": external_id, "airingAt": item.get("airingAt")}
    recorded = await records.record_payload(
        session,
        provider_slug="anilist",
        namespace_slug="episode",
        resource_type="episode",
        external_id=external_id,
        payload=stable,
        schema_version="anilist-graphql",
        canonical_url=f"https://anilist.co/anime/{media['id']}",
    )
    observation_id = await ingestion.record_observation(
        session,
        provider_record_id=recorded.record_id,
        mapper="anilist.episode",
        mapper_version="anilist-episode-v2",
        normalized_data=stable,
        schema_name="index.episode",
        schema_version="1",
    )
    entity_id, _ = await entities.ensure_entity(
        session,
        provider_record_id=recorded.record_id,
        kind="episode",
        audience="adult" if media.get("isAdult") is True else "general",
    )
    await entities.upsert_representation(
        session, provider_record_id=recorded.record_id, entity_id=entity_id
    )
    if number is not None:
        await presentation.add_names(
            session,
            entity_id=entity_id,
            provider_record_id=recorded.record_id,
            observation_id=observation_id,
            entries=[(f"Episode {number}", "en", "official")],
        )
    await graph.relation(
        session,
        work_id,
        entity_id,
        calendar_observation,
        relation_type="has-episode",
        json_pointer=f"/schedule/{index}",
        raw_relation="has-episode",
    )
    return entity_id
