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


def _work_entity(*, provider_slug: str, external_id: str):
    from apps.index.models import (
        Entity,
        Provider,
        ProviderNamespace,
        ProviderRecord,
        ProviderRepresentation,
        Work,
    )

    provider, _ = Provider.objects.get_or_create(
        slug=provider_slug, defaults={"name": provider_slug}
    )
    namespace, _ = ProviderNamespace.objects.get_or_create(
        provider=provider,
        slug="anime" if provider_slug != "bangumi" else "subject",
        defaults={"resource_type": ProviderNamespace.ResourceType.SUBJECT},
    )
    record = ProviderRecord.objects.create(
        namespace=namespace, external_id=external_id, origin="api", status="active"
    )
    entity = Entity.objects.create(kind=Entity.Kind.WORK)
    Work.objects.create(entity=entity, work_type=Work.WorkType.ANIME)
    ProviderRepresentation.objects.create(
        entity=entity,
        provider_record=record,
        mapping_kind=ProviderRepresentation.MappingKind.EXACT,
        method=ProviderRepresentation.Method.PROVIDER,
    )
    return entity


def _AIRun():
    from apps.ai.models import AIRun

    return AIRun.objects.create(
        use_case="entity_matching",
        provider="test",
        model="test",
        prompt_version="v1",
        input_hash="hash",
        status="succeeded",
    )


def test_apply_match_proposals_command_reports_summary() -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(
            match_apply_service,
            "run",
            lambda limit=None, apply=None, abstain_ineligible=True: {
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


def test_keep_pending_defers_ineligible_proposals() -> None:
    """An unattended run must not retire a pair it could not confirm."""
    from types import SimpleNamespace
    from unittest.mock import patch

    from apps.sync.services.match_apply_service import match_apply_service

    proposal = SimpleNamespace(
        pk="11111111-1111-1111-1111-111111111111",
        confidence=0.5,
        payload={"decision": "bind"},
        match_candidate=SimpleNamespace(
            pk="22222222-2222-2222-2222-222222222222",
            score=0.4,
            left_entity_id="33333333-3333-3333-3333-333333333333",
            right_entity_id="44444444-4444-4444-4444-444444444444",
            hard_conflicts=[],
            left_entity=SimpleNamespace(kind="work"),
            right_entity=SimpleNamespace(kind="work"),
        ),
    )
    with (
        patch(
            "apps.sync.services.match_apply_service.AIProposal.objects.filter"
        ) as proposals,
        patch.object(match_apply_service, "_decide") as decide,
    ):
        proposals.return_value.select_related.return_value.order_by.return_value.__getitem__.return_value = [
            proposal
        ]
        result = match_apply_service.run(limit=1, apply=True, abstain_ineligible=False)

    assert result["deferred"] == 1
    assert result["accepted"] == 0
    assert result["abstained"] == 0
    assert decide.call_count == 0


def test_pair_already_bound_by_another_rule_leaves_the_queue() -> None:
    """A proposal whose pair another rule already merged must not error forever.

    The official-id sweep and the AI batch cover overlapping pairs; without this
    the proposal stays pending, the daily task retries it, and the candidate
    raises "already resolve together" on every run.
    """
    from apps.ai.models import AIProposal
    from apps.index.models import (
        EntityRedirect,
        MatchCandidate,
        MergeEvent,
    )
    from apps.sync.services.match_apply_service import match_apply_service

    left = _work_entity(provider_slug="anilist", external_id="700")
    right = _work_entity(provider_slug="bangumi", external_id="701")
    merge = MergeEvent.objects.create(
        source_entity=left,
        target_entity=right,
        method=MergeEvent.Method.RULE,
        reason="test",
    )
    EntityRedirect.objects.create(
        source_entity=left, target_entity=right, merge_event=merge
    )
    candidate = MatchCandidate.objects.create(
        left_entity=left,
        right_entity=right,
        score=Decimal("1.0000"),
        runner_up_margin=Decimal("1.0000"),
        policy_version="title-similarity-v1",
    )
    run = _AIRun()
    proposal = AIProposal.objects.create(
        run=run,
        match_candidate=candidate,
        confidence=Decimal("0.9900"),
        payload={"decision": "bind"},
        status=AIProposal.Status.PENDING,
    )

    result = match_apply_service.run(limit=5, apply=True, abstain_ineligible=False)

    proposal.refresh_from_db()
    candidate.refresh_from_db()
    assert result["already_bound"] == 1
    assert result["errors"] == []
    assert proposal.status == AIProposal.Status.ACCEPTED
    assert candidate.status == MatchCandidate.Status.ABSTAINED


def test_user_library_conflict_is_recorded_not_retried() -> None:
    """A permanent conflict leaves the queue instead of erroring every run."""
    from apps.ai.models import AIProposal
    from apps.index.models import MatchCandidate
    from apps.sync.services.match_apply_service import match_apply_service

    left = _work_entity(provider_slug="anilist", external_id="800")
    right = _work_entity(provider_slug="bangumi", external_id="801")
    candidate = MatchCandidate.objects.create(
        left_entity=left,
        right_entity=right,
        score=Decimal("1.0000"),
        runner_up_margin=Decimal("1.0000"),
        policy_version="title-similarity-v1",
    )
    run = _AIRun()
    proposal = AIProposal.objects.create(
        run=run,
        match_candidate=candidate,
        confidence=Decimal("0.9900"),
        payload={"decision": "bind"},
        status=AIProposal.Status.PENDING,
    )

    from unittest.mock import patch

    from apps.index.exceptions import UserLibraryConflict
    from apps.index.models import MatchDecision

    def decide(*, candidate, outcome, decided_by, reason):
        # Only the bind is refused; the follow-up abstain has to go through.
        if outcome == MatchDecision.Outcome.BIND:
            raise UserLibraryConflict()
        return None

    with patch(
        "apps.sync.services.match_apply_service.entity_resolution_service.decide_candidate",
        side_effect=decide,
    ):
        result = match_apply_service.run(limit=5, apply=True, abstain_ineligible=False)

    proposal.refresh_from_db()
    assert result["blocked"] == 1
    assert result["errors"] == []
    assert proposal.status == AIProposal.Status.ABSTAINED


def test_same_title_years_apart_is_not_a_duplicate() -> None:
    """A remake shares its title with the original, and must not be bound to it.

    "SHAMAN KING" is both the 2001 series and the 2021 reboot; a title-similarity
    candidate scores them near identical, so the gate has to look at the era.
    """
    import datetime

    from apps.index.models import AnimeProfile, MatchCandidate, Work
    from apps.sync.services.match_apply_service import match_apply_service

    left = _work_entity(provider_slug="anilist", external_id="900")
    right = _work_entity(provider_slug="bangumi", external_id="901")
    AnimeProfile.objects.create(
        work=Work.objects.get(entity=left), premiered_on=datetime.date(2001, 7, 4)
    )
    AnimeProfile.objects.create(
        work=Work.objects.get(entity=right), premiered_on=datetime.date(2021, 4, 1)
    )
    candidate = MatchCandidate.objects.create(
        left_entity=left,
        right_entity=right,
        score=Decimal("1.0000"),
        runner_up_margin=Decimal("1.0000"),
        policy_version="title-similarity-v1",
    )

    reasons = match_apply_service._gate_reasons(
        type(
            "Proposal",
            (),
            {
                "confidence": Decimal("1.0"),
                "payload": {"decision": "bind"},
                "match_candidate": candidate,
            },
        )()
    )

    assert "release_year_conflict" in reasons

    # A pair without dates cannot be judged this way and stays eligible.
    AnimeProfile.objects.all().delete()
    assert "release_year_conflict" not in match_apply_service._gate_reasons(
        type(
            "Proposal",
            (),
            {
                "confidence": Decimal("1.0"),
                "payload": {"decision": "bind"},
                "match_candidate": candidate,
            },
        )()
    )
