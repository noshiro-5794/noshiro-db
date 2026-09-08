from decimal import Decimal
from io import StringIO

import pytest
from django.core.management import call_command

from apps.ai.models import AIProposal, AIRun
from apps.index.models import (
    Entity,
    EntityName,
    MatchCandidate,
    MatchDecision,
    MatchEvidence,
    Provider,
    ProviderNamespace,
    ProviderRecord,
    ProviderRepresentation,
    Work,
)
from apps.sync.services.match_apply_service import match_apply_service

pytestmark = pytest.mark.django_db(transaction=True)


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


def _pending_proposal(
    *, decision: str = "bind", confidence: str = "0.97"
) -> AIProposal:
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
    left, right = sorted((bangumi.pk, mal.pk), key=lambda value: str(value))
    candidate = MatchCandidate.objects.create(
        left_entity_id=left,
        right_entity_id=right,
        policy_version="title-similarity-mal-bangumi-v1",
        score="1.0000",
        runner_up_margin="0.5000",
        status=MatchCandidate.Status.PENDING,
        hard_conflicts=[],
    )
    MatchEvidence.objects.create(
        candidate=candidate,
        evidence_type="title_similarity",
        value={"provider_pair": "mal:bangumi"},
        weight=Decimal("1.0000"),
    )
    run = AIRun.objects.create(
        use_case="entity_matching",
        provider="openai_compatible",
        model="fake",
        prompt_version="v1",
        input_hash="x",
        status=AIRun.Status.SUCCEEDED,
    )
    return AIProposal.objects.create(
        run=run,
        match_candidate=candidate,
        proposal_type="entity_matching",
        payload={"decision": decision, "confidence": float(confidence), "reason": "x"},
        confidence=confidence,
    )


def test_dry_run_reports_eligible_bind_without_writing() -> None:
    proposal = _pending_proposal()

    result = match_apply_service.run(apply=False)

    assert result["would_bind"] == 1
    proposal.match_candidate.refresh_from_db()
    assert proposal.match_candidate.status == MatchCandidate.Status.PENDING
    assert proposal.status == AIProposal.Status.PENDING


def test_apply_binds_eligible_candidate_and_records_admin_decision() -> None:
    proposal = _pending_proposal()

    result = match_apply_service.run(apply=True)

    assert result["accepted"] == 1
    proposal.refresh_from_db()
    proposal.match_candidate.refresh_from_db()
    assert proposal.status == AIProposal.Status.ACCEPTED
    assert proposal.match_candidate.status == MatchCandidate.Status.ACCEPTED
    assert (
        MatchDecision.objects.filter(
            candidate=proposal.match_candidate,
            outcome=MatchDecision.Outcome.BIND,
            decided_by="admin_batch",
        ).exists()
        is True
    )


def test_apply_abstains_low_confidence_proposal() -> None:
    proposal = _pending_proposal(confidence="0.50")

    result = match_apply_service.run(apply=True)

    assert result["accepted"] == 0
    assert result["abstained"] == 1
    proposal.refresh_from_db()
    assert proposal.status == AIProposal.Status.ABSTAINED


def test_apply_match_proposals_command_reports_summary() -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(
            match_apply_service,
            "run",
            lambda limit=None, apply=None: {
                "processed": 1,
                "would_bind": 1,
                "accepted": 0,
                "abstained": 0,
                "errors": [],
            },
        )
        out = StringIO()
        call_command("apply_match_proposals", stdout=out)

    assert '"would_bind": 1' in out.getvalue()
