from decimal import Decimal

import pytest

from apps.index.models import (
    Entity,
    EntityRedirect,
    IndexCollection,
    IndexMembership,
    MergeEvent,
    MetricSnapshot,
    Provider,
    ProviderNamespace,
    ProviderRecord,
    Work,
)
from apps.index.selectors.projections import entity_queryset
from apps.index.services import popularity_service

pytestmark = pytest.mark.django_db


def _work(provider_slug: str, external_id: str) -> tuple[Entity, ProviderRecord]:
    provider, _ = Provider.objects.get_or_create(
        slug=provider_slug, defaults={"name": provider_slug}
    )
    namespace, _ = ProviderNamespace.objects.get_or_create(
        provider=provider,
        slug=provider_slug,
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
    collection, _ = IndexCollection.objects.get_or_create(
        slug="anime", defaults={"name": "Anime"}
    )
    IndexMembership.objects.update_or_create(
        collection=collection,
        entity=entity,
        defaults={"listing_state": IndexMembership.State.LISTED},
    )
    return entity, record


def _metric(entity: Entity, record: ProviderRecord, metric: str, value) -> None:
    MetricSnapshot.objects.create(
        entity=entity,
        provider_record=record,
        metric=metric,
        value=Decimal(str(value)),
    )


def test_popularity_ranks_by_normalised_engagement() -> None:
    quiet, quiet_record = _work("mal", "1")
    loud, loud_record = _work("mal", "2")
    _metric(quiet, quiet_record, "members", 100)
    _metric(loud, loud_record, "members", 100_000)

    popularity_service.refresh()

    quiet_work = Work.objects.get(entity=quiet)
    loud_work = Work.objects.get(entity=loud)
    assert loud_work.popularity == Decimal("100.000000")
    assert quiet_work.popularity == Decimal("0.000000")
    assert quiet_work.popularity_refreshed_at is not None


def test_popularity_ignores_reception_only_metrics() -> None:
    """A rating score does not tell us how many people care."""
    entity, record = _work("vndb", "v1")
    _metric(entity, record, "score", Decimal("9.5"))

    popularity_service.refresh()

    assert Work.objects.get(entity=entity).popularity == Decimal("0")


def test_merged_entities_share_the_stronger_signal() -> None:
    canonical, canonical_record = _work("mal", "10")
    absorbed, absorbed_record = _work("anilist", "20")
    plain, plain_record = _work("mal", "11")
    merge = MergeEvent.objects.create(
        source_entity=absorbed,
        target_entity=canonical,
        method=MergeEvent.Method.MANUAL,
        reason="test merge",
    )
    EntityRedirect.objects.create(
        source_entity=absorbed,
        target_entity=canonical,
        is_active=True,
        merge_event=merge,
    )
    _metric(canonical, canonical_record, "members", 600)
    _metric(plain, plain_record, "members", 400)
    _metric(absorbed, absorbed_record, "popularity", 90_000)

    popularity_service.refresh()

    # The canonical work collects both providers' engagement, so it outranks a
    # work that only ever saw the smaller MAL signal.
    assert (
        Work.objects.get(entity=canonical).popularity
        > Work.objects.get(entity=plain).popularity
    )


def test_catalogue_lists_hot_works_first() -> None:
    cold, cold_record = _work("mal", "100")
    hot, hot_record = _work("mal", "200")
    _metric(cold, cold_record, "members", 10)
    _metric(hot, hot_record, "members", 1_000_000)
    popularity_service.refresh()

    ordered = list(entity_queryset(collection="anime", ordering="popular"))

    assert [entity.pk for entity in ordered] == [hot.pk, cold.pk]
