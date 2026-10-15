import uuid

import pytest

from apps.index.models import (
    Entity,
    EntityName,
    Fact,
    MatchCandidate,
    MatchEvidence,
    Predicate,
    Provider,
    ProviderNamespace,
    ProviderRecord,
    ProviderRepresentation,
    Work,
)
from apps.index.services import provider_candidate_service

pytestmark = pytest.mark.django_db(transaction=True)

ANILIST_ANIME = ("anilist", "anime")
MAL_ANIME = ("mal", "anime")
BANGUMI_SUBJECT = ("bangumi", "subject")
VNDB_VN = ("vndb", "vn")


def _entity(
    *,
    provider_slug: str,
    namespace_slug: str,
    external_id: str,
    name: str,
    work_type: str | None = Work.WorkType.ANIME,
    release_date: str | None = None,
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
    ProviderRepresentation.objects.create(
        provider_record=record,
        entity=entity,
        mapping_kind=ProviderRepresentation.MappingKind.EXACT,
        method=ProviderRepresentation.Method.EXTERNAL_ID,
    )
    EntityName.objects.create(
        entity=entity,
        text=name,
        language="ja",
        kind=EntityName.Kind.ORIGINAL,
    )
    if work_type is not None:
        Work.objects.create(entity=entity, work_type=work_type)
    if release_date is not None:
        predicate, _ = Predicate.objects.get_or_create(
            slug="release-date",
            defaults={
                "name": "Release Date",
                "value_type": Predicate.ValueType.DATE,
            },
        )
        Fact.objects.create(
            entity=entity,
            predicate=predicate,
            value=release_date,
            value_hash=f"hash-{entity.pk}",
            status=Fact.Status.SELECTED,
        )
    return entity


def _shard(source: tuple[str, str] = ANILIST_ANIME) -> str:
    return provider_candidate_service.sweep_shard(
        source_provider=source[0],
        source_namespace=source[1],
        target_provider="bangumi",
        target_namespace="subject",
    )


def test_exact_title_match_creates_candidate_with_evidence() -> None:
    anilist = _entity(
        provider_slug="anilist",
        namespace_slug="anime",
        external_id="10",
        name="Mushoku Tensei 3",
    )
    EntityName.objects.create(
        entity=anilist,
        text="無職転生Ⅲ",
        language="ja",
        kind=EntityName.Kind.ORIGINAL,
    )
    _entity(
        provider_slug="bangumi",
        namespace_slug="subject",
        external_id="100",
        name="無職転生Ⅲ",
    )
    manga = _entity(
        provider_slug="bangumi",
        namespace_slug="subject",
        external_id="100-manga",
        name="無職転生Ⅲ",
        work_type=Work.WorkType.MANGA,
    )

    summary = provider_candidate_service.generate_candidates(
        min_similarity=0.6, top_k=5
    )

    assert summary["candidates_created"] == 1
    row = MatchCandidate.objects.select_related("left_entity", "right_entity").get()
    assert float(row.score) >= 0.99
    assert manga.id not in {row.left_entity_id, row.right_entity_id}
    evidence = MatchEvidence.objects.get(
        candidate=row, evidence_type="title_similarity"
    )
    assert evidence.value["similarity"] >= 0.99


def test_structured_evidence_carries_both_sides_and_the_comparison() -> None:
    source = _entity(
        provider_slug="anilist",
        namespace_slug="anime",
        external_id="14",
        name="Shingeki no Kyojin",
        release_date="2013-04-07",
    )
    target = _entity(
        provider_slug="bangumi",
        namespace_slug="subject",
        external_id="104",
        name="Shingeki no Kyojin",
        release_date="2013-04-07",
    )

    provider_candidate_service.generate_candidates(min_similarity=0.6, top_k=5)

    candidate = MatchCandidate.objects.get()
    evidence = MatchEvidence.objects.get(
        candidate=candidate, evidence_type="work_attributes"
    )
    value = evidence.value
    assert value["source_entity_id"] == str(source.pk)
    assert value["target_entity_id"] == str(target.pk)
    assert value["source"]["names"] == ["Shingeki no Kyojin"]
    assert value["target"]["release_date"] == "2013-04-07"
    assert value["comparison"]["release_year_delta"] == 0
    assert candidate.runner_up_margin == 0


def test_release_year_conflict_becomes_a_hard_conflict() -> None:
    _entity(
        provider_slug="anilist",
        namespace_slug="anime",
        external_id="15",
        name="Urusei Yatsura",
        release_date="1981-10-14",
    )
    _entity(
        provider_slug="bangumi",
        namespace_slug="subject",
        external_id="105",
        name="Urusei Yatsura",
        release_date="2022-10-14",
    )

    provider_candidate_service.generate_candidates(min_similarity=0.6, top_k=5)

    candidate = MatchCandidate.objects.get()
    assert candidate.hard_conflicts
    assert candidate.hard_conflicts[0]["type"] == "release_year_conflict"
    assert candidate.hard_conflicts[0]["delta_years"] == 41


def test_runner_up_margin_separates_the_best_match_from_the_second() -> None:
    _entity(
        provider_slug="anilist",
        namespace_slug="anime",
        external_id="16",
        name="Frieren Beyond Journeys End",
    )
    _entity(
        provider_slug="bangumi",
        namespace_slug="subject",
        external_id="106",
        name="Frieren Beyond Journeys End",
    )
    _entity(
        provider_slug="bangumi",
        namespace_slug="subject",
        external_id="107",
        name="Frieren Beyond Journeys",
    )

    provider_candidate_service.generate_candidates(min_similarity=0.3, top_k=5)

    candidates = list(MatchCandidate.objects.order_by("-score"))
    assert len(candidates) == 2
    assert candidates[0].runner_up_margin > 0
    assert float(candidates[0].runner_up_margin) == pytest.approx(
        float(candidates[0].score) - float(candidates[1].score), abs=1e-4
    )


def test_unrelated_titles_are_filtered_by_threshold() -> None:
    _entity(
        provider_slug="anilist",
        namespace_slug="anime",
        external_id="11",
        name="Totally Different Show",
    )
    _entity(
        provider_slug="bangumi",
        namespace_slug="subject",
        external_id="101",
        name="Unrelated Work Title",
    )

    summary = provider_candidate_service.generate_candidates(
        min_similarity=0.6, top_k=5
    )

    assert summary["candidates_created"] == 0
    assert summary["pairs"] == []


def test_candidate_generation_is_idempotent() -> None:
    _entity(
        provider_slug="anilist",
        namespace_slug="anime",
        external_id="12",
        name="Re Zero 4th Season",
    )
    _entity(
        provider_slug="bangumi",
        namespace_slug="subject",
        external_id="102",
        name="Re Zero 4th Season",
    )

    first = provider_candidate_service.generate_candidates(min_similarity=0.6, top_k=5)
    provider_candidate_service.reset_cursor(shard=_shard())
    second = provider_candidate_service.generate_candidates(min_similarity=0.6, top_k=5)

    assert first["candidates_created"] == 1
    assert second["candidates_created"] == 0


def test_dry_run_reports_pairs_without_writing_or_moving_the_cursor() -> None:
    _entity(
        provider_slug="anilist",
        namespace_slug="anime",
        external_id="13",
        name="A Shared Title",
    )
    _entity(
        provider_slug="bangumi",
        namespace_slug="subject",
        external_id="103",
        name="A Shared Title",
    )

    summary = provider_candidate_service.generate_candidates(
        min_similarity=0.6, top_k=5, create=False
    )

    assert summary["candidates_created"] == 0
    assert len(summary["pairs"]) == 1
    assert str(uuid.UUID(summary["pairs"][0]["source_entity"]))
    assert summary["cursor_after"] == summary["cursor_before"] == 0
    assert MatchCandidate.objects.count() == 0


def test_mal_source_can_match_bangumi_work() -> None:
    mal = _entity(
        provider_slug="mal",
        namespace_slug="anime",
        external_id="50",
        name="Sousou no Frieren",
    )
    _entity(
        provider_slug="bangumi",
        namespace_slug="subject",
        external_id="500",
        name="Sousou no Frieren",
    )

    summary = provider_candidate_service.generate_mal_bangumi_candidates(
        min_similarity=0.6,
        top_k=5,
    )

    assert summary["source_provider"] == "mal"
    assert summary["candidates_created"] == 1
    candidate = MatchCandidate.objects.select_related(
        "left_entity", "right_entity"
    ).get(policy_version=provider_candidate_service.POLICY_VERSION)
    evidence = MatchEvidence.objects.get(
        candidate=candidate, evidence_type="title_similarity"
    )
    assert evidence.value["provider_pair"] == "mal:bangumi"
    assert mal.id in {candidate.left_entity_id, candidate.right_entity_id}


def test_sweep_walks_past_entities_that_match_nothing() -> None:
    """The regression that stalled the catalogue: a sweep must keep moving.

    Entities that produce no pair used to stay at the front of the queue, so
    every run re-read the same names and the works behind them were never
    searched.
    """
    for index in range(2):
        _entity(
            provider_slug="anilist",
            namespace_slug="anime",
            external_id=str(600 + index),
            name=f"Nothing Like This {index}",
        )
    _entity(
        provider_slug="anilist",
        namespace_slug="anime",
        external_id="602",
        name="Eventually Matched",
    )
    _entity(
        provider_slug="bangumi",
        namespace_slug="subject",
        external_id="700",
        name="Eventually Matched",
    )

    first = provider_candidate_service.generate_candidates(
        min_similarity=0.6, top_k=5, limit=2
    )
    second = provider_candidate_service.generate_candidates(
        min_similarity=0.6, top_k=5, limit=2
    )

    assert first["candidates_created"] == 0
    assert first["cursor_after"] == 2
    assert second["candidates_created"] == 1
    assert second["cursor_after"] == 3


def test_completed_pass_resets_the_cursor_for_the_next_one() -> None:
    _entity(
        provider_slug="anilist",
        namespace_slug="anime",
        external_id="800",
        name="Only One",
    )
    _entity(
        provider_slug="bangumi",
        namespace_slug="subject",
        external_id="900",
        name="Only One",
    )

    provider_candidate_service.generate_candidates(min_similarity=0.6, top_k=5)
    closed = provider_candidate_service.generate_candidates(min_similarity=0.6, top_k=5)

    assert closed["completed_pass"] is True
    assert closed["candidates_created"] == 0
    assert provider_candidate_service._read_cursor(shard=_shard()) == 0

    # With the cursor back at the top, the pair is re-proposed idempotently.
    again = provider_candidate_service.generate_candidates(min_similarity=0.6, top_k=5)
    assert again["window"] == 1
    assert again["candidates_created"] == 0


def test_galgame_channel_matches_a_bangumi_game() -> None:
    _entity(
        provider_slug="vndb",
        namespace_slug="vn",
        external_id="v9000",
        name="Tsukihime",
        work_type=Work.WorkType.GALGAME,
    )
    _entity(
        provider_slug="bangumi",
        namespace_slug="subject",
        external_id="9000",
        name="Tsukihime",
        work_type=Work.WorkType.GAME,
    )

    summary = provider_candidate_service.generate_galgame_candidates(
        min_similarity=0.6, top_k=5
    )

    assert summary["source_work_types"] == [Work.WorkType.GALGAME]
    assert summary["candidates_created"] == 1


def test_anime_sweep_never_proposes_a_galgame() -> None:
    _entity(
        provider_slug="anilist",
        namespace_slug="anime",
        external_id="17",
        name="Shared Name",
        work_type=Work.WorkType.ANIME,
    )
    _entity(
        provider_slug="bangumi",
        namespace_slug="subject",
        external_id="108",
        name="Shared Name",
        work_type=Work.WorkType.GALGAME,
    )

    summary = provider_candidate_service.generate_candidates(
        min_similarity=0.6,
        top_k=5,
        source_work_types=(Work.WorkType.ANIME,),
        target_work_types=(Work.WorkType.ANIME,),
    )

    assert summary["candidates_created"] == 0
    assert MatchCandidate.objects.count() == 0


def test_decided_entities_are_skipped_on_a_fresh_pass() -> None:
    _entity(
        provider_slug="anilist",
        namespace_slug="anime",
        external_id="20",
        name="Skip Me",
    )
    _entity(
        provider_slug="bangumi",
        namespace_slug="subject",
        external_id="200",
        name="Skip Me",
    )
    first = provider_candidate_service.generate_candidates(min_similarity=0.6, top_k=5)
    assert first["candidates_created"] == 1

    provider_candidate_service.reset_cursor(shard=_shard())
    second = provider_candidate_service.generate_candidates(min_similarity=0.6, top_k=5)

    assert second["candidates_created"] == 0
    assert second["skipped_processed"] == 1
