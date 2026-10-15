import uuid
from unittest.mock import patch

import pytest
from django.conf import settings
from django.test import override_settings

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
from apps.sync.services.bangumi_link import (
    ATTEMPT_SCOPE,
    bangumi_link_service,
)

pytestmark = pytest.mark.django_db(transaction=True)


def _entity(
    *,
    provider_slug: str,
    namespace_slug: str,
    external_id: str,
    title: str,
    entity_id: uuid.UUID | None = None,
):
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
    entity = Entity.objects.create(id=entity_id, kind=Entity.Kind.WORK)
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


def _link_bangumi(entity: Entity, *, external_id: str) -> None:
    provider, _ = Provider.objects.get_or_create(
        slug="bangumi",
        defaults={"name": "Bangumi"},
    )
    namespace, _ = ProviderNamespace.objects.get_or_create(
        provider=provider,
        slug="subject",
        defaults={"resource_type": ProviderNamespace.ResourceType.SUBJECT},
    )
    record = ProviderRecord.objects.create(
        namespace=namespace,
        external_id=external_id,
        origin="api",
        status="active",
    )
    ProviderRepresentation.objects.create(
        provider_record=record,
        entity=entity,
        mapping_kind=ProviderRepresentation.MappingKind.EXACT,
        method=ProviderRepresentation.Method.PROVIDER,
    )


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
            "apps.sync.services.bangumi_link.ai_gateway.complete_json",
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
            "apps.sync.services.subject.subject_service.upsert_subject",
            return_value=bangumi_entity,
        ) as upsert,
        patch(
            "apps.sync.services.episode.episode_service.sync_subject_episodes",
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
            "apps.sync.services.bangumi_link.ai_gateway.complete_json",
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
            "apps.sync.services.subject.subject_service.upsert_subject",
        ) as upsert,
    ):
        result = bangumi_link_service.attempt(root=entity, apply=True)

    assert result["outcome"] == "abstained"
    upsert.assert_not_called()
    assert MatchDecision.objects.count() == 0


def test_run_missing_reaches_a_later_root_past_already_linked_roots() -> None:
    """Already linked roots must not spend the batch, or the sweep stalls."""
    for index in range(3):
        linked = _entity(
            provider_slug="mal",
            namespace_slug="anime",
            external_id=f"90{index}",
            title=f"Linked {index}",
            entity_id=uuid.UUID(int=index + 1),
        )
        _link_bangumi(linked, external_id=f"80{index}")
    target = _entity(
        provider_slug="mal",
        namespace_slug="anime",
        external_id="999",
        title="Unlinked Target",
        entity_id=uuid.UUID(int=99),
    )

    with patch.object(
        bangumi_link_service,
        "attempt",
        return_value={"root_entity_id": str(target.pk), "outcome": "no_match"},
    ) as attempt:
        result = bangumi_link_service.run_missing(limit=1)

    assert result["processed"] == 1
    attempt.assert_called_once_with(root=target, apply=False, force=False)


def test_run_missing_does_not_spend_the_batch_on_concluded_attempts() -> None:
    """The production stall: the first rows return skipped_existing forever."""
    roots = [
        _entity(
            provider_slug="mal",
            namespace_slug="anime",
            external_id=f"91{index}",
            title=f"Concluded {index}",
            entity_id=uuid.UUID(int=index + 1),
        )
        for index in range(3)
    ]
    target = _entity(
        provider_slug="mal",
        namespace_slug="anime",
        external_id="998",
        title="Still Open",
        entity_id=uuid.UUID(int=98),
    )

    def fake_attempt(*, root, apply=False, force=False):
        outcome = "no_match" if root.pk == target.pk else "skipped_existing"
        return {"root_entity_id": str(root.pk), "outcome": outcome}

    with patch.object(
        bangumi_link_service,
        "attempt",
        side_effect=fake_attempt,
    ) as attempt:
        result = bangumi_link_service.run_missing(limit=1)

    assert [item["outcome"] for item in result["results"]] == ["no_match"]
    assert result["processed"] == 1
    assert attempt.call_count == len(roots) + 1


@override_settings(BANGUMI_LINK_WALK_CAP=3)
def test_run_missing_stops_walking_at_the_configured_cap() -> None:
    for index in range(6):
        _entity(
            provider_slug="mal",
            namespace_slug="anime",
            external_id=f"92{index}",
            title=f"Walked {index}",
            entity_id=uuid.UUID(int=index + 1),
        )

    with patch.object(
        bangumi_link_service,
        "_needs_bangumi_link",
        return_value=False,
    ) as needs:
        result = bangumi_link_service.run_missing(limit=10)

    assert result["scanned"] == 3
    assert result["processed"] == 0
    assert needs.call_count == 3


def test_search_queries_cover_distinct_scripts() -> None:
    queries = bangumi_link_service._search_queries(
        names=[
            "Shingeki no Kyojin",
            "進撃の巨人",
            "进击的巨人",
            "Attack on Titan",
        ]
    )

    assert queries == ["進撃の巨人", "Shingeki no Kyojin", "进击的巨人"]


def test_search_queries_fall_back_to_the_remaining_names() -> None:
    queries = bangumi_link_service._search_queries(
        names=["Attack on Titan", "Shingeki no Kyojin", "SnK"]
    )

    assert queries == ["Attack on Titan", "Shingeki no Kyojin", "SnK"]


def test_link_bangumi_works_task_uses_the_configured_batch() -> None:
    from apps.sync.tasks.linking import link_bangumi_works_task

    with patch.object(
        bangumi_link_service,
        "run_missing",
        return_value={"processed": 0},
    ) as run:
        link_bangumi_works_task()

    run.assert_called_once_with(
        limit=settings.BANGUMI_LINK_BATCH_SIZE,
        apply=False,
        force=False,
    )


def test_link_sweeps_are_scheduled_and_registered() -> None:
    """A sweep nobody runs is not coverage, and a beat path must be importable."""
    from config.celery import app

    app.loader.import_default_modules()
    scheduled = {entry["task"] for entry in settings.CELERY_BEAT_SCHEDULE.values()}
    sweeps = {
        "apps.sync.tasks.linking.link_bangumi_works_task",
        "apps.sync.tasks.linking.recall_mal_links_task",
    }

    assert sweeps <= scheduled
    assert sweeps <= set(app.tasks)
