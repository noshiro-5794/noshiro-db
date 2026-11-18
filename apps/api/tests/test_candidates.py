from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from api.worker import candidates
from api.worker.candidates import ProviderCandidateService


@pytest.mark.asyncio
async def test_multilingual_recall_keeps_best_pair_and_runner_up_margin(monkeypatch):
    query = AsyncMock(
        side_effect=[
            [
                SimpleNamespace(entity_id="a", text="Alpha", sim=0.7),
                SimpleNamespace(entity_id="b", text="Beta", sim=0.6),
            ],
            [SimpleNamespace(entity_id="a", text="アルファ", sim=0.9)],
        ]
    )
    monkeypatch.setattr(candidates, "fetch", query)
    matches, margin = await ProviderCandidateService(
        SimpleNamespace(execute=AsyncMock())
    )._best_target_matches(
        names=["Alpha", "アルファ"],
        target_provider="bangumi",
        target_namespace="subject",
        target_work_types=("anime",),
        min_similarity=0.3,
        top_k=20,
    )
    assert [item["entity_id"] for item in matches] == ["a", "b"]
    assert matches[0]["source_text"] == "アルファ"
    assert margin == pytest.approx(0.3)


@pytest.mark.asyncio
async def test_decided_window_still_advances_cursor(monkeypatch):
    service = ProviderCandidateService(SimpleNamespace(execute=AsyncMock()))
    monkeypatch.setattr(
        service, "_sweep_window", AsyncMock(return_value=([("work", 5)], 4, 10, False))
    )
    monkeypatch.setattr(service, "_drop_decided", AsyncMock(return_value=[]))
    monkeypatch.setattr(service, "_names_for_entities", AsyncMock(return_value={}))
    write = AsyncMock()
    monkeypatch.setattr(service, "_write_cursor", write)
    result = await service.generate_candidates()
    assert result["cursor_after"] == 5
    write.assert_awaited_once()
    assert write.await_args.kwargs["cursor"] == 5


@pytest.mark.asyncio
async def test_dry_run_does_not_reset_completed_pass(monkeypatch):
    service = ProviderCandidateService(SimpleNamespace(execute=AsyncMock()))
    monkeypatch.setattr(service, "_sweep_window", AsyncMock(return_value=([], 10, 10, True)))
    write = AsyncMock()
    monkeypatch.setattr(service, "_write_cursor", write)
    result = await service.generate_candidates(create=False)
    assert result["completed_pass"] is True
    assert result["cursor_after"] == 10
    write.assert_not_awaited()


@pytest.mark.asyncio
async def test_candidates_keep_lowest_hit_when_none_reaches_evaluation_floor(monkeypatch):
    service = ProviderCandidateService(SimpleNamespace(execute=AsyncMock()))
    source = str(UUID(int=1))
    monkeypatch.setattr(
        service, "_sweep_window", AsyncMock(return_value=([(source, 1)], 0, 1, False))
    )
    monkeypatch.setattr(service, "_drop_decided", AsyncMock(return_value=[(source, 1)]))
    monkeypatch.setattr(service, "_names_for_entities", AsyncMock(return_value={source: ["Title"]}))
    matches = [
        {
            "entity_id": str(UUID(int=i)),
            "source_text": "Title",
            "target_text": "Other",
            "similarity": score,
        }
        for i, score in ((2, 0.4), (3, 0.35))
    ]
    monkeypatch.setattr(service, "_best_target_matches", AsyncMock(return_value=(matches, 0.05)))
    monkeypatch.setattr(service, "_attributes_for_entities", AsyncMock(return_value={}))
    monkeypatch.setattr(service, "_write_cursor", AsyncMock())
    result = await service.generate_candidates(create=False, eval_min_similarity=0.5)
    assert result["pairs_blocked"] == 2
    assert result["pairs_below_floor"] == 2
    assert len(result["pairs"]) == 1
    assert result["pairs"][0]["target_entity"] == str(UUID(int=2))


@pytest.mark.parametrize("year,conflict", [(2025, False), (2024, True), (None, False)])
def test_only_known_release_year_gap_blocks_binding(year, conflict):
    comparison, conflicts = ProviderCandidateService._compare(
        source={"release_year": 2026, "languages": ["ja", "en"], "episode_count": 12},
        target={"release_year": year, "languages": ["ja"], "episode_count": 24},
    )
    assert bool(conflicts) == conflict
    assert comparison["shared_languages"] == ["ja"]
    assert comparison["episode_count_delta"] == 12
