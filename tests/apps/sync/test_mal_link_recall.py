from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command

from apps.ai.models import AgentRun, AgentStep
from apps.index.models import (
    Entity,
    EntityName,
    MatchCandidate,
    MatchEvidence,
    Provider,
    ProviderNamespace,
    ProviderRecord,
    ProviderRepresentation,
    Work,
)
from apps.sync.services.mal_link_recall_service import (
    RecallMalOutput,
    mal_link_recall_service,
)

pytestmark = pytest.mark.django_db(transaction=True)


def test_not_found_output_allows_missing_confidence() -> None:
    output = RecallMalOutput.model_validate(
        {"decision": "not_found", "reason": "No precise MAL entry."}
    )

    assert output.confidence == 0


def test_matched_alias_normalizes_to_found() -> None:
    output = RecallMalOutput.model_validate(
        {
            "decision": "matched",
            "mal_id": 62954,
            "confidence": 0.97,
            "reason": "Same title and date.",
        }
    )

    assert output.decision == "found"


def _anime_entity(
    *,
    provider_slug: str,
    namespace_slug: str,
    external_id: str,
    title: str,
) -> Entity:
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
        language="ja",
        kind=EntityName.Kind.ORIGINAL,
    )
    return entity


def test_ensure_candidate_links_existing_mal_entity_with_evidence() -> None:
    bangumi = _anime_entity(
        provider_slug="bangumi",
        namespace_slug="subject",
        external_id="607933",
        title="万古至尊 李云霄传",
    )
    mal = _anime_entity(
        provider_slug="mal",
        namespace_slug="anime",
        external_id="62954",
        title="万古至尊 李云霄传",
    )
    with patch(
        "apps.sync.services.mal_link_recall_service.mal_import_service.import_anime"
    ) as import_anime:
        candidate_id, linked_root_id = mal_link_recall_service._ensure_candidate(
            root=bangumi,
            mal_id=62954,
            confidence=0.96,
            reason="Same Chinese title and 2026-07 start.",
        )

    assert candidate_id is not None
    assert linked_root_id == str(mal.pk)
    import_anime.assert_not_called()
    candidate = MatchCandidate.objects.get(pk=candidate_id)
    assert candidate.policy_version == "mal-agent-recall-v1"
    assert candidate.status == MatchCandidate.Status.PENDING
    assert float(candidate.score) == pytest.approx(0.96)
    evidence = MatchEvidence.objects.get(
        candidate=candidate, evidence_type="agent_mal_recall"
    )
    assert evidence.value["mal_id"] == 62954


def test_has_pending_mal_candidate_sees_open_candidate() -> None:
    bangumi = _anime_entity(
        provider_slug="bangumi",
        namespace_slug="subject",
        external_id="572768",
        title="一念永恒 完结季",
    )
    mal = _anime_entity(
        provider_slug="mal",
        namespace_slug="anime",
        external_id="62248",
        title="一念永恒 完结季",
    )
    assert mal_link_recall_service._has_pending_mal_candidate(bangumi) is False

    left, right = sorted((bangumi.pk, mal.pk), key=lambda value: str(value))
    MatchCandidate.objects.create(
        left_entity_id=left,
        right_entity_id=right,
        policy_version="title-similarity-mal-bangumi-v1",
        score="1.0",
        runner_up_margin="0.5",
        status=MatchCandidate.Status.PENDING,
        hard_conflicts=[],
    )
    assert mal_link_recall_service._has_pending_mal_candidate(bangumi) is True


def test_recall_mal_links_command_reports_summary() -> None:
    with patch(
        "apps.sync.management.commands.recall_mal_links.mal_link_recall_service.run_missing",
        return_value={
            "policy_version": "mal-agent-recall-v1",
            "processed": 1,
            "results": [{"root_entity_id": "x", "outcome": "not_found"}],
        },
    ) as run:
        out = StringIO()
        call_command("recall_mal_links", "--limit", "5", "--no-evaluate", stdout=out)

    run.assert_called_once_with(limit=5, evaluate=False, force=False)
    assert '"not_found"' in out.getvalue()


def test_failed_attempt_frees_idempotency_key_for_retry() -> None:
    bangumi = _anime_entity(
        provider_slug="bangumi",
        namespace_slug="subject",
        external_id="595884",
        title="Test Show",
    )
    old = AgentRun.objects.create(
        kind=AgentRun.Kind.ADMIN_ENRICH,
        status=AgentRun.Status.FAILED,
        error="old failure",
        idempotency_scope="mal-recall:v1",
        idempotency_key="bangumi:595884",
        metadata={"scopes": ["knowledge:read", "mal:read"]},
    )

    def fake_driver_run(run, **kwargs):
        run.status = AgentRun.Status.SUCCEEDED
        run.error = ""
        run.save(update_fields=["status", "error", "updated_at"])
        AgentStep.objects.create(
            run=run,
            sequence=1,
            kind=AgentStep.Kind.MODEL,
            status=AgentStep.Status.SUCCEEDED,
            output={
                "decision": "not_found",
                "mal_id": None,
                "confidence": 0.0,
                "reason": "No precise MAL entry.",
            },
        )
        return run

    fake = type("FakeDriver", (), {"run": staticmethod(fake_driver_run)})()
    with patch(
        "apps.sync.services.mal_link_recall_service.AgentLoopDriver",
        return_value=fake,
    ):
        result = mal_link_recall_service.recall_one(
            root=bangumi,
            evaluate=False,
        )

    assert result["outcome"] == "not_found"
    old.refresh_from_db()
    assert old.idempotency_key == ""
    assert (
        AgentRun.objects.filter(
            idempotency_scope="mal-recall:v1",
            idempotency_key="bangumi:595884",
        ).count()
        == 1
    )
