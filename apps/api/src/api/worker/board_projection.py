"""Rebuild the canonical weekly board from retained provider schedule evidence."""

import json
import os
from datetime import UTC, date, datetime, time
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.presentation.fragments import fetch
from api.contexts.presentation.identity import load_redirects, root_of
from api.contexts.scheduling import board_rules as rules
from api.worker import calendar_write


async def ensure_board(session: AsyncSession, moment: datetime) -> Any:
    await fetch(session, "SELECT pg_advisory_xact_lock(74329401)", {})
    boards = await fetch(session, "SELECT * FROM airing_board WHERE status='active' FOR UPDATE", {})
    if not boards:
        identifier = await calendar_write.create_board(
            session, season_key="", observation_id=None, item_count=0, effective_from=moment
        )
        boards = await fetch(session, "SELECT * FROM airing_board WHERE id=:id", {"id": identifier})
    board = boards[0]
    local = moment.astimezone(ZoneInfo(os.environ.get("DEPLOYMENT_TIME_ZONE") or "Asia/Shanghai"))
    season = f"{local.year}Q{(local.month - 1) // 3 + 1}"
    if board.season_key != season:
        if rules.season_switch_allowed(season, today=local.date()):
            await calendar_write.archive_active_boards(session)
            identifier = await calendar_write.create_board(
                session,
                season_key=season,
                observation_id=board.observation_id,
                item_count=0,
                effective_from=moment,
            )
            return (
                await fetch(session, "SELECT * FROM airing_board WHERE id=:id", {"id": identifier})
            )[0]
        metadata = {
            **(board.metadata or {}),
            "rollover_pending": season,
            "rollover_effective_on": rules.season_switch_date(season).isoformat(),
        }
        await fetch(
            session,
            "UPDATE airing_board SET metadata=CAST(:metadata AS jsonb),updated_at=now() "
            "WHERE id=:id RETURNING id",
            {"id": board.id, "metadata": json.dumps(metadata)},
        )
    return board


def board_window(moment: datetime) -> tuple[datetime, datetime]:
    local = moment.astimezone(ZoneInfo(os.environ.get("DEPLOYMENT_TIME_ZONE") or "Asia/Shanghai"))
    first = date(local.year, local.month, 1)
    zone = ZoneInfo("Asia/Tokyo")
    return (
        datetime.combine(rules.add_months(first, -1), time(), tzinfo=zone).astimezone(UTC),
        datetime.combine(rules.add_months(first, 2), time(), tzinfo=zone).astimezone(UTC),
    )


async def candidates(
    session: AsyncSession, board: Any, moment: datetime
) -> list[rules.CandidateBar]:
    start, end = board_window(moment)
    redirects = await load_redirects(session)
    events = await fetch(
        session,
        "SELECT event.*,p.slug AS provider FROM airing_event event "
        "JOIN provider_observation o ON o.id=event.observation_id "
        "JOIN provider_record r ON r.id=o.provider_record_id "
        "JOIN provider_namespace ns ON ns.id=r.namespace_id "
        "JOIN provider p ON p.id=ns.provider_id JOIN work w ON w.entity_id=event.work_id "
        "WHERE (event.precision='weekday' AND "
        "((CAST(:observation AS uuid) IS NOT NULL AND event.observation_id=:observation) OR "
        "(CAST(:observation AS uuid) IS NULL AND EXISTS (SELECT 1 FROM "
        "provider_current_observation c WHERE c.observation_id=o.id)))) OR "
        "(event.precision='minute' AND event.starts_at>=:start AND event.starts_at<:end "
        "AND w.work_type='anime' AND p.slug='anilist' AND ns.slug='calendar') "
        "ORDER BY event.starts_at,event.weekday,event.collection_doing DESC,event.id",
        {"observation": board.observation_id, "start": start, "end": end},
    )
    roots = {root_of(row.work_id, redirects) for row in events}
    formats = {
        row.entity_id: row.format
        for row in await fetch(
            session,
            "SELECT w.entity_id,p.format FROM work w JOIN entity e ON e.id=w.entity_id "
            "LEFT JOIN anime_profile p ON p.work_id=w.entity_id "
            "WHERE w.entity_id=ANY(:ids) AND e.lifecycle='active' AND e.kind='work'",
            {"ids": list(roots)},
        )
    }
    bars = []
    for event in events:
        root = root_of(event.work_id, redirects)
        if root not in formats:
            continue
        minute = event.precision == "minute"
        bars.append(
            rules.CandidateBar(
                entity_id=root,
                weekday=event.starts_at.weekday() + 1 if minute else event.weekday,
                starts_at=event.starts_at if minute else None,
                timezone=event.timezone or "UTC" if minute else "",
                precision="minute" if minute else "weekday",
                status="scheduled" if minute else "tentative",
                provider="anilist" if minute else "bangumi",
                format=formats[root] or "",
                observation_id=event.observation_id,
            )
        )
    mal_works = {}
    for row in await fetch(
        session,
        "SELECT r.external_id,rep.entity_id FROM entity_representation rep "
        "JOIN provider_record r ON r.id=rep.provider_record_id "
        "JOIN provider_namespace ns ON ns.id=r.namespace_id "
        "JOIN provider p ON p.id=ns.provider_id JOIN entity e ON e.id=rep.entity_id "
        "WHERE rep.is_active AND p.slug='mal' AND ns.slug='anime' AND e.lifecycle='active'",
        {},
    ):
        try:
            mal_works[int(row.external_id)] = row.entity_id
        except (TypeError, ValueError):
            continue
    seasons = {board.season_key, rules.next_season_key(board.season_key)}
    for observation in await fetch(
        session,
        "SELECT DISTINCT o.id,o.normalized_data FROM provider_observation o "
        "JOIN provider_current_observation c ON c.observation_id=o.id "
        "JOIN provider_record r ON r.id=c.provider_record_id "
        "JOIN provider_namespace ns ON ns.id=r.namespace_id "
        "JOIN provider p ON p.id=ns.provider_id "
        "WHERE o.schema_name='index.schedule' AND p.slug='mal' AND ns.slug='season'",
        {},
    ):
        normalized = observation.normalized_data or {}
        if normalized.get("season_key") not in seasons:
            continue
        for item in normalized.get("items") or []:
            if not isinstance(item, dict):
                continue
            bar = rules.mal_item_bar(
                item=item, mal_works=mal_works, observation_id=observation.id, now=start, end=end
            )
            if bar is not None:
                bars.append(bar)
    return [bar for bar in bars if bar.weekday is None or rules.format_allowed(bar.format)]


def project(bars: list[rules.CandidateBar], works: set[UUID]) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, int | None], list[rules.CandidateBar]] = {}
    for bar in bars:
        grouped.setdefault((bar.entity_id, bar.weekday), []).append(bar)
    entries = []
    for (identifier, weekday), alternatives in grouped.items():
        if identifier not in works:
            continue
        chosen = rules.choose_bar(alternatives)
        agrees = [bar for bar in alternatives if rules.corroborates(chosen, bar)]
        entries.append(
            {
                "work_id": str(identifier),
                "weekday": weekday,
                "starts_at": chosen.starts_at.isoformat() if chosen.starts_at else None,
                "timezone": chosen.timezone,
                "duration_minutes": chosen.duration_minutes,
                "precision": chosen.precision,
                "status": chosen.status,
                "decision": "consensus" if agrees else "source_priority",
                "confidence": "1.0000" if agrees else "0.9500",
                "source_refs": [
                    {
                        "provider": bar.provider,
                        "namespace": {"bangumi": "subject", "mal": "anime"}.get(
                            bar.provider, "calendar"
                        ),
                        "external_id": bar.external_id,
                        "observation_id": str(bar.observation_id) if bar.observation_id else "",
                        "precision": bar.precision,
                        "starts_at": bar.starts_at.isoformat() if bar.starts_at else "",
                        "role": rules.source_role(chosen=chosen, bar=bar),
                    }
                    for bar in [chosen, *agrees]
                ],
            }
        )
    return entries


async def rebuild(session: AsyncSession, *, now: datetime | None = None) -> dict[str, Any]:
    moment = now or datetime.now(UTC)
    async with session.begin_nested():
        board = await ensure_board(session, moment)
        bars = await candidates(session, board, moment)
        works = {
            row.entity_id
            for row in await fetch(
                session,
                "SELECT entity_id FROM work WHERE entity_id=ANY(:ids)",
                {"ids": list({bar.entity_id for bar in bars})},
            )
        }
        entries = project(bars, works)
        await fetch(
            session,
            "DELETE FROM airing_board_entry WHERE board_id=:id RETURNING id",
            {"id": board.id},
        )
        if entries:
            await fetch(
                session,
                "INSERT INTO airing_board_entry "
                "(id,board_id,work_id,weekday,starts_at,timezone,duration_minutes,precision,status,"
                "decision,confidence,source_refs,region,created_at,updated_at) "
                "SELECT gen_random_uuid(),:board,v.work_id,v.weekday,v.starts_at,v.timezone,"
                "v.duration_minutes,v.precision,v.status,v.decision,v.confidence,v.source_refs,'',"
                "now(),now() FROM jsonb_to_recordset(CAST(:entries AS jsonb)) AS v "
                "(work_id uuid,weekday smallint,starts_at timestamptz,timezone text,"
                "duration_minutes integer,precision text,status text,decision text,"
                "confidence numeric,source_refs jsonb) RETURNING id",
                {"board": board.id, "entries": json.dumps(entries)},
            )
        await fetch(
            session,
            "UPDATE airing_board SET item_count=:count,metadata=CAST(:metadata AS jsonb),"
            "effective_until=NULL,updated_at=now() WHERE id=:id RETURNING id",
            {
                "id": board.id,
                "count": len(entries),
                "metadata": json.dumps(
                    {
                        "projection": "field-fusion-v2",
                        "candidate_count": len(bars),
                        "generated_at": moment.isoformat(),
                    }
                ),
            },
        )
    return {
        "board_id": str(board.id),
        "season_key": board.season_key,
        "entries": len(entries),
        "candidates": len(bars),
    }
