from unittest.mock import patch

import pytest

from apps.ai.models import AgentRun
from apps.index.models import (
    Entity,
    EntityName,
    MatchCandidate,
    MatchDecision,
    Provider,
    ProviderNamespace,
    ProviderRecord,
    ProviderRepresentation,
    Work,
)
from apps.sync.services.bangumi_link_service import (
    ATTEMPT_SCOPE,
    bangumi_link_service,
)

pytestmark = pytest.mark.django_db(transaction=True)


def _entity(*, provider_slug: str, namespace_slug: str, external_id: str, title: str):
    provider, _ = Provider.objects.get_or_create(
        slug=provider_slug,
        defaults={"name": provider_slug.title()},
    )
    namespace, _ = ProviderNamespace.objects.get_or_create(
        provider=provider,
        slug=namespace_slug,
        defaults={"resource_type": ProviderNamespace.ResourceType.SUBJECT},
    )
    record = ProviderRecord.objects.create(
        namespace=namespace,
        external_id=external_id,
        origin="api",
        status="active",
    )
    entity = Entity.objects.create(kind=Entity.Kind.WORK)
    Work.objects.create(entity=entity, work_type=Work.WorkType.ANIME)
    ProviderRepresentation.objects.create(
        provider_record=record,
        entity=entity,
        mapping_kind=ProviderRepresentation.MappingKind.EXACT,
        method=ProviderRepresentation.Method.PROVIDER,
    )
    EntityName.objects.create(
        entity=entity,
        text=title,
        language="en",
        kind=EntityName.Kind.ROMANIZED,
    )
    return entity


def test_needs_bangumi_link_distinguishes_linked_and_missing_works() -> None:
    linked = _entity(
        provider_slug="mal",
        namespace_slug="anime",
        external_id="100",
        title="Test Anime",
    )
    bangumi_entity = _entity(
        provider_slug="bangumi",
        namespace_slug="subject",
        external_id="23456",
        title="Test Anime",
    )
    # Bangumi representation on the same canonical entity means already linked.
    ProviderRepresentation.objects.filter(entity=bangumi_entity).update(entity=linked)

    assert bangumi_link_service._needs_bangumi_link(linked) is False

    missing = _entity(
        provider_slug="mal",
        namespace_slug="anime",
        external_id="101",
        title="Another Anime",
    )
    assert bangumi_link_service._needs_bangumi_link(missing) is True


def test_no_match_records_idempotent_attempt_without_search_sync() -> None:
    entity = _entity(
        provider_slug="mal",
        namespace_slug="anime",
        external_id="200",
        title="Missing Title",
    )

    with patch.object(
        bangumi_link_service,
        "_search_bangumi",
        return_value=([], [], True),
    ) as search:
        result = bangumi_link_service.attempt(root=entity, apply=False)

    assert result["outcome"] == "no_match"
    search.assert_called_once()
    assert (
        AgentRun.objects.filter(
            idempotency_scope=ATTEMPT_SCOPE,
            metadata__outcome="no_match",
        ).count()
        == 1
    )

    rerun = bangumi_link_service.attempt(root=entity, apply=False)
    assert rerun["outcome"] == "skipped_existing"


def test_high_confidence_subject_is_synced_and_bound() -> None:
    mal_entity = _entity(
        provider_slug="mal",
        namespace_slug="anime",
        external_id="300",
        title="Test Anime",
    )
    bangumi_entity = _entity(
        provider_slug="bangumi",
        namespace_slug="subject",
        external_id="23456",
        title="Test Anime",
    )
    candidates = [
        {
            "id": 23456,
            "name": "Test Anime",
            "name_cn": "测试动画",
            "date": "2026-04-01",
            "url": "https://bgm.tv/subject/23456",
        }
    ]
    with (
        patch.object(
            bangumi_link_service,
            "_search_bangumi",
            return_value=(candidates, [], True),
        ),
        patch(
            "apps.sync.services.bangumi_link_service.ai_gateway.complete_json",
            return_value=(
                {
                    "decision": "found",
                    "subject_id": 23456,
                    "confidence": 0.97,
                    "reason": "Same title and April 2026 anime.",
                },
                {"input_tokens": 10, "output_tokens": 5},
            ),
        ),
        patch(
            "apps.sync.services.subject_service.subject_service.upsert_subject",
            return_value=bangumi_entity,
        ) as upsert,
        patch(
            "apps.sync.services.episode_service.episode_service.sync_subject_episodes",
        ) as episodes,
    ):
        result = bangumi_link_service.attempt(root=mal_entity, apply=True)

    assert result["outcome"] == "linked"
    assert result["subject_id"] == 23456
    upsert.assert_called_once_with(23456)
    episodes.assert_called_once_with(23456)
    decision = MatchDecision.objects.get(outcome=MatchDecision.Outcome.BIND)
    assert decision.candidate.status == MatchCandidate.Status.ACCEPTED


def test_hallucinated_subject_id_never_triggers_sync() -> None:
    entity = _entity(
        provider_slug="mal",
        namespace_slug="anime",
        external_id="400",
        title="Test Anime",
    )
    candidates = [
        {
            "id": 999,
            "name": "Wrong Candidate",
            "date": "2025-01-01",
            "url": "https://bgm.tv/subject/999",
        }
    ]
    with (
        patch.object(
            bangumi_link_service,
            "_search_bangumi",
            return_value=(candidates, [], True),
        ),
        patch(
            "apps.sync.services.bangumi_link_service.ai_gateway.complete_json",
            return_value=(
                {
                    "decision": "found",
                    "subject_id": 1111,
                    "confidence": 0.99,
                    "reason": "Invented id.",
                },
                {"input_tokens": 10, "output_tokens": 5},
            ),
        ),
        patch(
            "apps.sync.services.subject_service.subject_service.upsert_subject",
        ) as upsert,
    ):
        result = bangumi_link_service.attempt(root=entity, apply=True)

    assert result["outcome"] == "abstained"
    upsert.assert_not_called()
    assert MatchDecision.objects.count() == 0
