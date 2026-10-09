from unittest.mock import patch

import pytest
from django.test import override_settings

from apps.ai.models import AgentRun, AIClaim, ClaimEvidence
from apps.ai.services import schedule_completion_service
from apps.ai.tools.web import WebSearchOutput
from apps.index.models import (
    AiringBoardEntry,
    Entity,
    EntityName,
    Work,
)
from apps.index.services.airing_board import airing_board_service

pytestmark = pytest.mark.django_db(transaction=True)


def _board_entry() -> tuple[Entity, AiringBoardEntry]:
    entity = Entity.objects.create(kind=Entity.Kind.WORK)
    Work.objects.create(entity=entity, work_type=Work.WorkType.ANIME)
    EntityName.objects.create(
        entity=entity,
        text="Re:Zero",
        language="ja",
        kind=EntityName.Kind.ORIGINAL,
    )
    board = airing_board_service.refresh(
        observation=None,
        season_key="2026Q3",
        item_count=1,
    )
    entry = AiringBoardEntry.objects.create(
        board=board,
        work=Work.objects.get(entity=entity),
        weekday=2,
        precision=AiringBoardEntry.Precision.WEEKDAY,
        status=AiringBoardEntry.Status.TENTATIVE,
        source_refs=[{"provider": "bangumi"}],
    )
    return entity, entry


@override_settings(
    WEB_SEARCH_PROVIDER="none",
    WEB_SEARCH_API_KEY="",
)
def test_run_skips_when_web_search_is_unavailable() -> None:
    _board_entry()

    summary = schedule_completion_service.run()

    assert summary["pending"] == 1
    assert summary["skipped_no_search"] == 1
    assert AgentRun.objects.count() == 0


@override_settings(
    WEB_SEARCH_PROVIDER="tavily",
    WEB_SEARCH_API_KEY="test-key",
    AI_ENRICH_MIN_CONFIDENCE=0.7,
)
def test_run_applies_high_confidence_web_slot_and_keeps_claim() -> None:
    entity, entry = _board_entry()
    with (
        patch(
            "apps.ai.services.schedule_completion.web_search_tool.execute",
            return_value=WebSearchOutput(
                available=True,
                results=[
                    {
                        "title": "Re:Zero",
                        "url": "https://example.test/schedule",
                        "content": "Wednesday 22:00 (JST)",
                    }
                ],
            ),
        ),
        patch(
            "apps.ai.services.schedule_completion.ai_gateway.complete_json",
            return_value=(
                {
                    "decision": "accept",
                    "weekday": 3,
                    "time": "22:00",
                    "timezone": "Asia/Tokyo",
                    "duration_minutes": 24,
                    "confidence": 0.95,
                    "reason": "Web schedule states Wednesday 22:00 JST.",
                },
                {},
            ),
        ),
    ):
        summary = schedule_completion_service.run()

    assert summary["accepted"] == 1
    assert summary["applied"] == 1
    entry.refresh_from_db()
    assert entry.precision == AiringBoardEntry.Precision.MINUTE
    assert entry.starts_at is not None
    assert entry.decision == AiringBoardEntry.Decision.AI
    claim = AIClaim.objects.get(claim_type="schedule_completion")
    assert claim.target_entity_id == entity.id
    assert ClaimEvidence.objects.filter(claim=claim).exists()
    assert any(ref.get("claim_id") == str(claim.id) for ref in entry.source_refs)


@override_settings(
    WEB_SEARCH_PROVIDER="tavily",
    WEB_SEARCH_API_KEY="test-key",
    AI_ENRICH_MIN_CONFIDENCE=0.9,
)
def test_low_confidence_accepted_slot_creates_proposal_without_applying() -> None:
    _, entry = _board_entry()
    with (
        patch(
            "apps.ai.services.schedule_completion.web_search_tool.execute",
            return_value=WebSearchOutput(
                available=True,
                results=[
                    {"title": "x", "url": "https://example.test", "content": "Wed 22"}
                ],
            ),
        ),
        patch(
            "apps.ai.services.schedule_completion.ai_gateway.complete_json",
            return_value=(
                {
                    "decision": "accept",
                    "weekday": 3,
                    "time": "22:00",
                    "timezone": "Asia/Tokyo",
                    "duration_minutes": 24,
                    "confidence": 0.8,
                    "reason": "Search result.",
                },
                {},
            ),
        ),
    ):
        summary = schedule_completion_service.run()

    assert summary["accepted"] == 1
    assert summary["applied"] == 0
    entry.refresh_from_db()
    assert entry.precision == AiringBoardEntry.Precision.WEEKDAY
    assert AIClaim.objects.filter(status=AIClaim.Status.ACCEPTED).exists() is False
