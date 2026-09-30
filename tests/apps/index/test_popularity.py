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


def _work(
    provider_slug: str,
    external_id: str,
    *,
    work_type: str = Work.WorkType.ANIME,
) -> tuple[Entity, ProviderRecord]:
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
    Work.objects.create(entity=entity, work_type=work_type)
    collection_slug = "galgame" if work_type == Work.WorkType.GALGAME else "anime"
    collection, _ = IndexCollection.objects.get_or_create(
        slug=collection_slug, defaults={"name": collection_slug.title()}
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


def test_anime_rank_by_anilist_popularity() -> None:
    quiet, quiet_record = _work("anilist", "1")
    loud, loud_record = _work("anilist", "2")
    _metric(quiet, quiet_record, "popularity", 100)
    _metric(loud, loud_record, "popularity", 100_000)

    popularity_service.refresh()

    quiet_work = Work.objects.get(entity=quiet)
    loud_work = Work.objects.get(entity=loud)
    assert loud_work.popularity == Decimal("100.000000")
    assert quiet_work.popularity == Decimal("0.000000")
    assert quiet_work.popularity_refreshed_at is not None


def test_secondary_sources_do_not_move_the_ranking() -> None:
    """MAL and Bangumi reach is stored, but AniList decides the anime order."""
    decided_by_anilist, anilist_record = _work("anilist", "30")
    only_secondary, mal_record = _work("mal", "31")
    bangumi_record_owner, bangumi_record = _work("bangumi", "32")
    _metric(decided_by_anilist, anilist_record, "popularity", 50_000)
    _metric(only_secondary, mal_record, "members", 900_000)
    _metric(bangumi_record_owner, bangumi_record, "votes", 800_000)

    popularity_service.refresh()

    assert Work.objects.get(entity=decided_by_anilist).popularity == Decimal(
        "100.000000"
    )
    assert Work.objects.get(entity=only_secondary).popularity == Decimal("0")
    assert Work.objects.get(entity=bangumi_record_owner).popularity == Decimal("0")


def test_galgame_rank_by_vndb_rating_count() -> None:
    niche, niche_record = _work("vndb", "v1", work_type=Work.WorkType.GALGAME)
    famous, famous_record = _work("vndb", "v2", work_type=Work.WorkType.GALGAME)
    bangumi_only, bangumi_record = _work(
        "bangumi", "900", work_type=Work.WorkType.GALGAME
    )
    _metric(niche, niche_record, "votes", 120)
    _metric(famous, famous_record, "votes", 40_000)
    _metric(bangumi_only, bangumi_record, "votes", 90_000)

    popularity_service.refresh()

    assert Work.objects.get(entity=famous).popularity == Decimal("100.000000")
    assert Work.objects.get(entity=niche).popularity == Decimal("0.000000")
    # Same metric name, different provider: Bangumi does not rank galgames.
    assert Work.objects.get(entity=bangumi_only).popularity == Decimal("0")


def test_a_source_only_ranks_the_type_it_belongs_to() -> None:
    galgame_with_anilist_reach, anilist_record = _work(
        "anilist", "40", work_type=Work.WorkType.GALGAME
    )
    anime_with_vndb_votes, vndb_record = _work("vndb", "v40")
    _metric(galgame_with_anilist_reach, anilist_record, "popularity", 20_000)
    _metric(anime_with_vndb_votes, vndb_record, "votes", 20_000)

    popularity_service.refresh()

    assert Work.objects.get(entity=galgame_with_anilist_reach).popularity == Decimal(
        "0"
    )
    assert Work.objects.get(entity=anime_with_vndb_votes).popularity == Decimal("0")


def test_merged_entities_share_the_stronger_signal() -> None:
    canonical, canonical_record = _work("anilist", "10")
    absorbed, absorbed_record = _work("anilist", "20")
    plain, plain_record = _work("anilist", "11")
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
    _metric(canonical, canonical_record, "popularity", 600)
    _metric(plain, plain_record, "popularity", 400)
    # The merged record carried the larger AniList count, so the canonical work
    # inherits it.
    _metric(absorbed, absorbed_record, "popularity", 90_000)

    popularity_service.refresh()

    assert Work.objects.get(entity=canonical).popularity == Decimal("100.000000")
    assert (
        Work.objects.get(entity=canonical).popularity
        > Work.objects.get(entity=plain).popularity
    )


def test_catalogue_lists_hot_works_first() -> None:
    cold, cold_record = _work("anilist", "100")
    hot, hot_record = _work("anilist", "200")
    _metric(cold, cold_record, "popularity", 10)
    _metric(hot, hot_record, "popularity", 1_000_000)
    popularity_service.refresh()

    ordered = list(entity_queryset(collection="anime", ordering="popular"))

    assert [entity.pk for entity in ordered] == [hot.pk, cold.pk]
