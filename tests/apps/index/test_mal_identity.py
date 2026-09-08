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
from apps.index.services import mal_identity_service

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
