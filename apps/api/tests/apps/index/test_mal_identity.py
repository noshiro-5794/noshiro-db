from unittest.mock import patch

import pytest

from apps.index.models import (
    Entity,
    EntityRedirect,
    EntityRepresentation,
    Fact,
    MatchCandidate,
    MergeEvent,
    Predicate,
    Provider,
    ProviderNamespace,
    ProviderRecord,
    Work,
)
from apps.index.services import entity_resolution_service, mal_identity_service

pytestmark = pytest.mark.django_db(transaction=True)


def _work_entity(
    *, provider_slug: str, namespace_slug: str, external_id: str
) -> Entity:
    provider, _ = Provider.objects.get_or_create(
        slug=provider_slug,
        defaults={"name": provider_slug},
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
    EntityRepresentation.objects.create(
        provider_record=record,
        entity=entity,
        mapping_kind=EntityRepresentation.MappingKind.EXACT,
        method=EntityRepresentation.Method.PROVIDER,
    )
    return entity


def _record_mal_id_fact(*, entity: Entity, mal_id: int) -> None:
    predicate, _ = Predicate.objects.get_or_create(
        slug=mal_identity_service.ANILIST_ID_MAL_PREDICATE,
        defaults={"name": "AniList MAL id", "value_type": Predicate.ValueType.NUMBER},
    )
    Fact.objects.create(
        entity=entity,
        predicate=predicate,
        value=mal_id,
        value_hash=f"mal-{mal_id}",
    )


def _redirect_into(*, source: Entity, target: Entity) -> None:
    """Redirect ``source`` into ``target`` without flipping its lifecycle.

    Production still carries redirect rows whose source was never moved to
    ``MERGED``, so a sweep that trusts ``lifecycle`` alone walks them as if
    they could still bind.
    """
    event = MergeEvent.objects.create(
        source_entity=source,
        target_entity=target,
        method=MergeEvent.Method.RULE,
        reason="legacy backfill",
    )
    EntityRedirect.objects.create(
        source_entity=source,
        target_entity=target,
        merge_event=event,
    )


def _add_mal_representation(*, entity: Entity, external_id: str) -> None:
    """Represent a second MAL record on an entity a sweep may already have bound."""
    namespace = ProviderNamespace.objects.get(provider__slug="mal", slug="anime")
    record = ProviderRecord.objects.create(
        namespace=namespace,
        external_id=external_id,
        origin="api",
        status="active",
    )
    EntityRepresentation.objects.create(
        provider_record=record,
        entity=entity,
        mapping_kind=EntityRepresentation.MappingKind.AGGREGATE,
        method=EntityRepresentation.Method.PROVIDER,
    )


def test_official_mal_anilist_link_binds_canonical_works() -> None:
    mal_entity = _work_entity(
        provider_slug="mal",
        namespace_slug="anime",
        external_id="5114",
    )
    anilist_entity = _work_entity(
        provider_slug="anilist",
        namespace_slug="anime",
        external_id="1000",
    )
    _record_mal_id_fact(entity=anilist_entity, mal_id=5114)

    summary = mal_identity_service.reconcile_official_links()

    assert summary["bound"] == 1
    assert summary["abstained"] == 0
    canonical = (
        mal_entity.id
        if not EntityRedirect.objects.filter(source_entity=mal_entity).exists()
        else EntityRedirect.objects.get(source_entity=mal_entity).target_entity_id
    )
    assert canonical == anilist_entity.id or canonical == mal_entity.id
    assert MatchCandidate.objects.filter(
        policy_version=mal_identity_service.OFFICIAL_POLICY,
        status=MatchCandidate.Status.ACCEPTED,
    ).exists()


def test_official_dry_run_creates_no_candidates() -> None:
    mal_entity = _work_entity(
        provider_slug="mal",
        namespace_slug="anime",
        external_id="1",
    )
    anilist_entity = _work_entity(
        provider_slug="anilist",
        namespace_slug="anime",
        external_id="200",
    )
    _record_mal_id_fact(entity=anilist_entity, mal_id=1)

    summary = mal_identity_service.reconcile_official_links(
        create=False,
        apply=False,
    )

    assert summary["candidates_created"] == 0
    assert summary["bound"] == 0
    assert MatchCandidate.objects.count() == 0
    assert mal_entity.lifecycle == Entity.Lifecycle.ACTIVE


def test_each_pair_commits_on_its_own() -> None:
    """A failure on a later pair must not roll back the merges already made.

    The sweep used to run inside one transaction: a time limit or a single bad
    pair discarded every binding the run had produced, which is how the daily
    season task merged nothing for weeks.
    """
    _work_entity(provider_slug="mal", namespace_slug="anime", external_id="10")
    first_anilist = _work_entity(
        provider_slug="anilist", namespace_slug="anime", external_id="100"
    )
    _record_mal_id_fact(entity=first_anilist, mal_id=10)
    _work_entity(provider_slug="mal", namespace_slug="anime", external_id="11")
    second_anilist = _work_entity(
        provider_slug="anilist", namespace_slug="anime", external_id="101"
    )
    _record_mal_id_fact(entity=second_anilist, mal_id=11)

    original = entity_resolution_service.decide_candidate
    calls = {"n": 0}

    def explode_on_second(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] > 1:
            raise RuntimeError("provider hiccup")
        return original(*args, **kwargs)

    with (
        patch.object(
            entity_resolution_service, "decide_candidate", side_effect=explode_on_second
        ),
        pytest.raises(RuntimeError),
    ):
        mal_identity_service.reconcile_official_links()

    # The first merge survived the second pair's failure.
    assert (
        MatchCandidate.objects.filter(
            policy_version=mal_identity_service.OFFICIAL_POLICY,
            status=MatchCandidate.Status.ACCEPTED,
        ).count()
        == 1
    )
    merged = EntityRedirect.objects.filter(is_active=True).count()
    assert merged == 1


def test_limit_bounds_one_run() -> None:
    for index in range(3):
        mal_entity = _work_entity(
            provider_slug="mal", namespace_slug="anime", external_id=str(100 + index)
        )
        anilist_entity = _work_entity(
            provider_slug="anilist",
            namespace_slug="anime",
            external_id=str(900 + index),
        )
        _record_mal_id_fact(entity=anilist_entity, mal_id=100 + index)
        assert mal_entity.pk != anilist_entity.pk

    summary = mal_identity_service.reconcile_official_links(limit=2)

    assert summary["examined"] == 2
    assert summary["bound"] == 2


def test_official_id_link_abstains_when_the_premieres_disagree() -> None:
    """AniList's idMal is authoritative, but a remake is still a different work.

    The mapping (or one side's date) is wrong when the same title sits a
    generation apart, and binding them silently rewrites both.
    """
    import datetime

    from apps.index.models import AnimeProfile, CandidateDecision

    mal_entity = _work_entity(
        provider_slug="mal", namespace_slug="anime", external_id="4190"
    )
    anilist_entity = _work_entity(
        provider_slug="anilist", namespace_slug="anime", external_id="119675"
    )
    AnimeProfile.objects.create(
        work=Work.objects.get(entity=mal_entity), premiered_on=datetime.date(2001, 7, 4)
    )
    AnimeProfile.objects.create(
        work=Work.objects.get(entity=anilist_entity),
        premiered_on=datetime.date(2021, 4, 1),
    )
    _record_mal_id_fact(entity=anilist_entity, mal_id=4190)

    summary = mal_identity_service.reconcile_official_links()

    assert summary["bound"] == 0
    assert summary["abstained"] == 1
    assert CandidateDecision.objects.filter(
        outcome=CandidateDecision.Outcome.ABSTAIN
    ).exists()


def test_bounded_run_reaches_bindable_pair_behind_redirected_records() -> None:
    """A batch must not be spent on records that are already merged away.

    The ordering restarts at the first MAL id on every run, so counting
    redirected rows against ``limit`` would leave the daily task binding the
    same few records forever and never examining the rest of the catalogue.
    """
    canonical = _work_entity(
        provider_slug="anilist", namespace_slug="anime", external_id="1"
    )
    for index in range(3):
        mal_entity = _work_entity(
            provider_slug="mal", namespace_slug="anime", external_id=str(index + 1)
        )
        _redirect_into(source=mal_entity, target=canonical)
    later_mal = _work_entity(
        provider_slug="mal", namespace_slug="anime", external_id="5000"
    )
    later_anilist = _work_entity(
        provider_slug="anilist", namespace_slug="anime", external_id="9500"
    )
    _record_mal_id_fact(entity=later_anilist, mal_id=5000)

    summary = mal_identity_service.reconcile_official_links(limit=3)

    assert summary["skipped_redirected"] == 3
    assert summary["examined"] == 1
    assert summary["bound"] == 1
    redirects = entity_resolution_service.redirect_map()
    assert entity_resolution_service.resolve_with(
        redirects, later_mal.pk
    ) == entity_resolution_service.resolve_with(redirects, later_anilist.pk)


def test_budget_counts_unresolved_records_not_rows_walked() -> None:
    """With ``limit=k`` the k-th unresolved record is still considered."""
    canonical = _work_entity(
        provider_slug="anilist", namespace_slug="anime", external_id="1"
    )
    for index in range(4):
        mal_entity = _work_entity(
            provider_slug="mal", namespace_slug="anime", external_id=str(10 + index)
        )
        _redirect_into(source=mal_entity, target=canonical)
    for index in range(3):
        _work_entity(
            provider_slug="mal", namespace_slug="anime", external_id=str(5000 + index)
        )
        twin = _work_entity(
            provider_slug="anilist",
            namespace_slug="anime",
            external_id=str(9000 + index),
        )
        _record_mal_id_fact(entity=twin, mal_id=5000 + index)

    summary = mal_identity_service.reconcile_official_links(limit=2)

    assert summary["skipped_redirected"] == 4
    assert summary["examined"] == 2
    assert summary["bound"] == 2


def test_walk_follows_the_merges_the_same_run_makes() -> None:
    """The redirect map is a snapshot, so the run's own merges update it.

    One entity can carry representations of several MAL records, and a pair
    committed earlier in the sweep redirects it. Without following that
    redirect a later row of the same entity would be examined as if it were
    still canonical and spend budget it cannot use.
    """
    twin = _work_entity(
        provider_slug="anilist", namespace_slug="anime", external_id="700"
    )
    mal_entity = _work_entity(
        provider_slug="mal", namespace_slug="anime", external_id="100"
    )
    _record_mal_id_fact(entity=twin, mal_id=100)
    _add_mal_representation(entity=mal_entity, external_id="999")

    summary = mal_identity_service.reconcile_official_links()

    assert summary["bound"] == 1
    assert summary["examined"] == 1
    assert summary["skipped_redirected"] == 1
