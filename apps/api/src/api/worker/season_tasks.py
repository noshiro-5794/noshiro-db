"""Seasonal provider promotion, weekly projection and quarter rollover."""

import os
from collections.abc import Awaitable, Callable
from typing import Any

from celery import shared_task

from api.contexts.presentation.fragments import fetch
from api.contexts.scheduling import board_rules
from api.shared import dispatch
from api.worker import anilist_import, board_projection, calendar_tasks, mal_import, season_sources
from api.worker.candidates import ProviderCandidateService
from api.worker.runtime import run
from api.worker.session import session_scope


async def isolated(runner: Callable[[], Awaitable[dict[str, Any]]]) -> dict[str, Any]:
    try:
        detail = await runner()
    except Exception as error:
        unavailable = getattr(error, "unavailable_reason", None)
        return {
            "status": "unavailable" if unavailable else "failed",
            "unavailable_reason": unavailable,
            "error": f"{type(error).__name__}: {error}",
            "retryable": bool(getattr(error, "retryable", False)),
            "retry_after": getattr(error, "retry_after", None),
        }
    return {"status": "succeeded", "detail": detail}


async def saved_ids(provider: str, maximum: int | None) -> list[str]:
    async with session_scope() as session:
        rows = await fetch(
            session,
            "SELECT DISTINCT r.external_id FROM provider_record r "
            "JOIN provider_namespace ns ON ns.id=r.namespace_id "
            "JOIN provider p ON p.id=ns.provider_id WHERE p.slug=:provider "
            "AND ns.slug=:namespace AND r.status='active' AND r.latest_revision_id IS NOT NULL "
            "AND NOT EXISTS (SELECT 1 FROM entity_representation rep "
            "JOIN provider_record promoted ON promoted.id=rep.provider_record_id "
            "JOIN provider_namespace pn ON pn.id=promoted.namespace_id "
            "WHERE rep.is_active AND pn.provider_id=p.id AND pn.slug='anime' "
            "AND promoted.external_id=r.external_id "
            "AND (CAST(:provider AS text)<>'anilist' OR promoted.status='active')) "
            "ORDER BY r.external_id LIMIT :maximum",
            {
                "provider": provider,
                "namespace": "schedule-item" if provider == "mal" else "season-item",
                "maximum": max(1, int(maximum)) if maximum else None,
            },
        )
        return [row.external_id for row in rows]


async def promote(provider: str, identifiers: list[str]) -> int:
    imported = 0
    importer = (
        mal_import.import_saved_anime if provider == "mal" else anilist_import.import_saved_media
    )
    for identifier in identifiers:
        try:
            async with session_scope() as session:
                # Recheck identity inside the importer's transaction when another run has
                # promoted the same seasonal item since target selection.
                existing = await fetch(
                    session,
                    "SELECT rep.entity_id FROM entity_representation rep "
                    "JOIN provider_record r ON r.id=rep.provider_record_id "
                    "JOIN provider_namespace ns ON ns.id=r.namespace_id "
                    "JOIN provider p ON p.id=ns.provider_id WHERE p.slug=:provider "
                    "AND ns.slug=:namespace AND r.external_id=:id AND r.status='active' "
                    "AND rep.is_active LIMIT 1",
                    {
                        "provider": provider,
                        "namespace": "schedule-item" if provider == "mal" else "anime",
                        "id": identifier,
                    },
                )
                if existing and provider == "mal":
                    imported += 1
                    continue
                entity_id = await importer(session, int(identifier))
                imported += int(entity_id is not None)
        except (TypeError, ValueError):
            continue
    return imported


async def candidates(provider: str) -> dict[str, Any]:
    async with session_scope() as session:
        service = ProviderCandidateService(session)
        maximum = int(os.environ.get("MATCH_CANDIDATE_BATCH_SIZE", "2000"))
        if provider == "mal":
            return await service.generate_mal_bangumi_candidates(limit=maximum, skip_processed=True)
        return await service.generate_anime_candidates(create=True, limit=maximum)


async def rebuild_board() -> dict[str, Any]:
    async with session_scope() as session:
        return await board_projection.rebuild(session)


async def evaluate_candidates(identifiers: list[str]) -> int:
    count = 0
    for identifier in identifiers:
        await dispatch.enqueue(
            "apps.ai.tasks.evaluate_match_candidate_task", {"candidate_id": str(identifier)}
        )
        count += 1
    return count


async def mal_pipeline(
    *, fetch_season: bool = True, evaluate: bool = False, max_items: int | None = None
) -> dict[str, Any]:
    season = await season_sources.sync_mal() if fetch_season else None
    identifiers = await saved_ids("mal", max_items)
    imported = await promote("mal", identifiers)
    generated = await candidates("mal")
    board = await rebuild_board()
    dispatched = await evaluate_candidates(generated["created_ids"]) if evaluate else 0
    return {
        "season": season,
        "saved_anime_ids": len(identifiers),
        "imported_entities": imported,
        "identity": None,
        "mal_candidates": generated,
        "board_projection": board,
        "ai_evaluations_dispatched": dispatched,
    }


async def anilist_leg(maximum: int | None) -> dict[str, Any]:
    snapshot = await season_sources.sync_anilist()
    imported = await promote("anilist", await saved_ids("anilist", maximum))
    generated = await candidates("anilist")
    return {
        "snapshot": snapshot,
        "imported": imported,
        "candidates": generated,
        "candidate_ids": list(generated.get("created_ids") or []),
    }


async def season_pipeline(
    *, max_items_per_source: int | None = None, evaluate: bool = False
) -> dict[str, Any]:
    sources = {
        "anilist": await isolated(lambda: anilist_leg(max_items_per_source)),
        "mal": await isolated(lambda: mal_pipeline(max_items=max_items_per_source)),
    }
    anilist = sources["anilist"].get("detail") or {}
    mal = sources["mal"].get("detail") or {}
    identifiers = list(
        dict.fromkeys(
            [
                *(anilist.get("candidates") or {}).get("created_ids", []),
                *(mal.get("mal_candidates") or {}).get("created_ids", []),
            ]
        )
    )
    dispatched = await evaluate_candidates(identifiers) if evaluate else 0
    board = await isolated(rebuild_board)
    statuses = [source["status"] for source in sources.values()]
    overall = (
        "succeeded"
        if all(value == "succeeded" for value in statuses)
        else "partial"
        if "succeeded" in statuses
        else "failed"
    )
    return {
        "sources": sources,
        "board": board,
        "overall": overall,
        "anilist_snapshot": anilist.get("snapshot"),
        "anilist_imported": anilist.get("imported"),
        "anilist_candidates": {
            "created": len(anilist.get("candidate_ids") or []),
            "ids": anilist.get("candidate_ids") or [],
        }
        if anilist
        else None,
        "mal": mal or None,
        "ai_evaluations_dispatched": dispatched,
    }


async def safe_prefetch(runner: Callable[[], Awaitable[dict[str, Any]]]) -> dict[str, Any]:
    try:
        return {"status": "succeeded", "result": await runner()}
    except Exception as error:
        return {"status": "failed", "error": f"{type(error).__name__}: {error}"[:2000]}


async def rollover() -> dict[str, Any]:
    today = season_sources.local_today()
    current = f"{today.year}Q{(today.month - 1) // 3 + 1}"
    async with session_scope() as session:
        boards = await fetch(
            session, "SELECT * FROM airing_board WHERE status='active' LIMIT 1", {}
        )
    if not boards:
        return {"action": "initialized", "pipeline": await season_pipeline()}
    board = boards[0]
    if board.season_key == current:
        return {"action": "none", "season_key": current}
    switch_allowed = board_rules.season_switch_allowed(current, today=today)

    async def bangumi_prefetch() -> dict[str, Any]:
        if not switch_allowed:
            return await season_sources.prefetch_bangumi()
        return await calendar_tasks.synchronize(
            sync_subject_details=False, job_id=None, lease_owner="season-rollover"
        )

    prefetch = {
        "mal": await safe_prefetch(season_sources.sync_mal),
        "anilist": await safe_prefetch(season_sources.sync_anilist),
        "bangumi": await safe_prefetch(bangumi_prefetch),
    }
    if not switch_allowed:
        return {
            "action": "prefetched",
            "pending_season": current,
            "active_season": board.season_key,
            "prefetch": prefetch,
        }
    pipeline = await season_pipeline()
    async with session_scope() as session:
        boards = await fetch(
            session, "SELECT season_key FROM airing_board WHERE status='active' LIMIT 1", {}
        )
        switched = bool(boards and boards[0].season_key == current)
        retired = []
        if switched:
            retired = await fetch(
                session,
                "UPDATE sync_state SET status='finished',updated_at=now() "
                "WHERE task_name='airing_daily' AND shard NOT LIKE :suffix RETURNING id",
                {"suffix": f"%:{current}"},
            )
    return {
        "action": "switched" if switched else "failed",
        "season_key": current,
        "prefetch": prefetch,
        "pipeline": pipeline,
        "retired_sync_shards": len(retired),
    }


@shared_task(  # type: ignore[untyped-decorator]
    name="apps.sync.tasks.mal.run_mal_season_pipeline_task",
    queue="sync",
    soft_time_limit=3600,
    time_limit=3900,
)
def run_mal_season_pipeline_task(
    *, fetch_season: bool = True, evaluate: bool = False, max_items: int | None = None
) -> dict[str, Any]:
    result: dict[str, Any] = run(
        mal_pipeline(fetch_season=fetch_season, evaluate=evaluate, max_items=max_items)
    )
    return result


@shared_task(  # type: ignore[untyped-decorator]
    name="apps.sync.tasks.season.run_season_pipeline_task",
    queue="sync",
    soft_time_limit=5400,
    time_limit=6000,
)
def run_season_pipeline_task(
    *, max_items_per_source: int | None = None, evaluate: bool = False
) -> dict[str, Any]:
    result: dict[str, Any] = run(
        season_pipeline(max_items_per_source=max_items_per_source, evaluate=evaluate)
    )
    return result


@shared_task(  # type: ignore[untyped-decorator]
    name="apps.sync.tasks.season.check_season_rollover_task",
    queue="sync",
    soft_time_limit=6000,
    time_limit=6600,
)
def check_season_rollover_task() -> dict[str, Any]:
    result: dict[str, Any] = run(rollover())
    return result
