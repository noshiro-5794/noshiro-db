from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from api.worker import airing_daily


@pytest.mark.asyncio
async def test_refresh_uses_the_target_provider(monkeypatch):
    providers = ("mal", "anilist", "bangumi")
    targets = [airing_daily.AiringTarget(provider, "42", "work") for provider in providers]
    monkeypatch.setattr(airing_daily, "board_targets", AsyncMock(return_value=(targets, "2026Q4")))
    monkeypatch.setattr(airing_daily, "start_window", AsyncMock(return_value=(0, 2)))
    monkeypatch.setattr(airing_daily, "finish_window", AsyncMock())
    fetchers = [AsyncMock(return_value={"provider": provider}) for provider in providers]
    importers = [AsyncMock() for _ in providers]
    session = object()
    result = await airing_daily.sync_day(
        session,
        now=datetime(2026, 11, 16, tzinfo=UTC),
        batch_size=3,
        fetch_anime=fetchers[0],
        fetch_media=fetchers[1],
        fetch_subject=fetchers[2],
        import_anime=importers[0],
        import_media=importers[1],
        import_subject=importers[2],
    )
    assert result["processed"] == 3
    assert result["finished"] is True
    for fetcher, importer, provider in zip(fetchers, importers, providers, strict=True):
        fetcher.assert_awaited_once_with(42)
        importer.assert_awaited_once_with(session, {"provider": provider})


@pytest.mark.asyncio
@pytest.mark.parametrize("status,current", [("finished", 3), ("idle", 3)])
async def test_completed_window_skips_last_target(monkeypatch, status, current):
    query = AsyncMock(return_value=[SimpleNamespace(id=1, current_id=current, status=status)])
    monkeypatch.setattr(airing_daily, "fetch", query)
    assert await airing_daily.start_window(
        object(), shard="today", total_count=3, batch_size=10
    ) == (3, 2)
    query.assert_awaited_once()


@pytest.mark.asyncio
async def test_failed_provider_preserves_retry_cursor(monkeypatch):
    targets = [airing_daily.AiringTarget("anilist", "42", "work")]
    monkeypatch.setattr(airing_daily, "board_targets", AsyncMock(return_value=(targets, "2026Q4")))
    monkeypatch.setattr(airing_daily, "start_window", AsyncMock(return_value=(0, 0)))
    failed = AsyncMock()
    monkeypatch.setattr(airing_daily, "fail_window", failed)
    fetch_anime = AsyncMock()
    importer = AsyncMock()
    with pytest.raises(RuntimeError, match="provider unavailable"):
        await airing_daily.sync_day(
            object(),
            now=datetime(2026, 11, 16, tzinfo=UTC),
            batch_size=1,
            fetch_anime=fetch_anime,
            fetch_media=AsyncMock(side_effect=RuntimeError("provider unavailable")),
            fetch_subject=AsyncMock(),
            import_anime=importer,
            import_media=importer,
            import_subject=importer,
        )
    fetch_anime.assert_not_awaited()
    importer.assert_not_awaited()
    assert failed.await_args.kwargs["current_id"] == 0
