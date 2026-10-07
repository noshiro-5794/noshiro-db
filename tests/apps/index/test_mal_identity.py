from unittest.mock import patch

import pytest

from apps.index.models import (
    Entity,
    EntityRedirect,
    Fact,
    MatchCandidate,
    Predicate,
    Provider,
    ProviderNamespace,
    ProviderRecord,
    ProviderRepresentation,
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
    ProviderRepresentation.objects.create(
        provider_record=record,
        entity=entity,
        mapping_kind=ProviderRepresentation.MappingKind.EXACT,
        method=ProviderRepresentation.Method.PROVIDER,
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

    from apps.index.models import AnimeProfile, MatchDecision

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
    assert MatchDecision.objects.filter(outcome=MatchDecision.Outcome.ABSTAIN).exists()
