from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command

from apps.index.models import (
    Contributor,
    Credit,
    CurrentObservation,
    Entity,
    EntityName,
    Observation,
    Provider,
    ProviderNamespace,
    ProviderRecord,
    ProviderRepresentation,
    Work,
)
from apps.index.services import knowledge_ingestion_service

pytestmark = pytest.mark.django_db(transaction=True)


def _run(*args, **kwargs) -> str:
    out = StringIO()
    call_command(*args, stdout=out, **kwargs)
    return out.getvalue()


def _anilist_entity() -> Entity:
    provider, _ = Provider.objects.get_or_create(
        slug="anilist", defaults={"name": "AniList"}
    )
    namespace, _ = ProviderNamespace.objects.get_or_create(
        provider=provider,
        slug="anime",
        defaults={"resource_type": ProviderNamespace.ResourceType.SUBJECT},
    )
    record = ProviderRecord.objects.create(
        namespace=namespace, external_id="1", origin="api", status="active"
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
        text="Some Anime",
        language="en",
        kind=EntityName.Kind.ORIGINAL,
    )
    return entity


def _observed_work_record(*, namespace: ProviderNamespace) -> ProviderRecord:
    record = ProviderRecord.objects.create(
        namespace=namespace, external_id="2", origin="api", status="active"
    )
    observation = Observation.objects.create(
        provider_record=record,
        origin=Observation.Origin.LEGACY,
        schema_name="index.work",
        schema_version="1",
        normalized_data={"title": "Work"},
        normalized_hash="hash-2",
    )
    CurrentObservation.objects.create(
        provider_record=record,
        mapper="legacy",
        schema_name="index.work",
        observation=observation,
    )
    return record


def _contributor_entity(
    *, namespace: ProviderNamespace
) -> tuple[Entity, ProviderRecord]:
    record = ProviderRecord.objects.create(
        namespace=namespace, external_id="3", origin="api", status="active"
    )
    entity = Entity.objects.create(kind=Entity.Kind.CONTRIBUTOR)
    ProviderRepresentation.objects.create(
        provider_record=record,
        entity=entity,
        mapping_kind=ProviderRepresentation.MappingKind.EXACT,
        method=ProviderRepresentation.Method.EXTERNAL_ID,
    )
    EntityName.objects.create(
        entity=entity,
        provider_record=record,
        text="Some Contributor",
        language="en",
        kind=EntityName.Kind.OFFICIAL,
    )
    return entity, record


def _observed_episode_entity(
    *, namespace: ProviderNamespace
) -> tuple[Entity, Observation]:
    record = ProviderRecord.objects.create(
        namespace=namespace, external_id="4", origin="api", status="active"
    )
    observation = Observation.objects.create(
        provider_record=record,
        origin=Observation.Origin.LEGACY,
        schema_name="index.episode",
        schema_version="1",
        normalized_data={"episode": 1},
        normalized_hash="hash-episode",
    )
    CurrentObservation.objects.create(
        provider_record=record,
        mapper="anilist.episode",
        schema_name="index.episode",
        observation=observation,
    )
    entity = Entity.objects.create(kind=Entity.Kind.EPISODE)
    ProviderRepresentation.objects.create(
        provider_record=record,
        entity=entity,
        mapping_kind=ProviderRepresentation.MappingKind.EXACT,
        method=ProviderRepresentation.Method.PROVIDER,
    )
    return entity, observation


def test_generate_match_candidates_dry_run_reports_counts() -> None:
    _anilist_entity()

    output = _run("generate_match_candidates", dry_run=True)

    assert "dry-run" in output
    assert "anilist_entities=1" in output
    assert "candidates_created=0" in output


def test_backfill_entity_name_observations_links_legacy_names() -> None:
    provider, _ = Provider.objects.get_or_create(
        slug="anilist", defaults={"name": "AniList"}
    )
    namespace, _ = ProviderNamespace.objects.get_or_create(
        provider=provider,
        slug="anime",
        defaults={"resource_type": ProviderNamespace.ResourceType.SUBJECT},
    )
    work_record = _observed_work_record(namespace=namespace)
    work_entity = Entity.objects.create(kind=Entity.Kind.WORK)
    ProviderRepresentation.objects.create(
        provider_record=work_record,
        entity=work_entity,
        mapping_kind=ProviderRepresentation.MappingKind.EXACT,
        method=ProviderRepresentation.Method.PROVIDER,
    )
    work = Work.objects.create(
        entity=work_entity,
        work_type=Work.WorkType.ANIME,
    )
    contributor_entity, contributor_record = _contributor_entity(namespace=namespace)
    contributor = Contributor.objects.create(
        entity=contributor_entity,
        kind=Contributor.Kind.PERSON,
    )
    observation = Observation.objects.filter(provider_record=work_record).first()
    Credit.objects.create(
        work=work,
        contributor=contributor,
        role="Director",
        observation=observation,
    )

    name = EntityName.objects.get(
        entity=contributor_entity,
        provider_record=contributor_record,
    )
    assert name.observation_id is None

    output = _run("backfill_entity_name_observations")
    assert "[dry-run] orphan_names=1 linkable=1 unlinked=0" in output
    name.refresh_from_db()
    assert name.observation_id is None

    output = _run("backfill_entity_name_observations", apply=True)
    assert "[applied] orphan_names=1 linkable=1 unlinked=0" in output
    name.refresh_from_db()
    assert name.observation_id == observation.id


def test_backfill_anilist_episode_types_records_ep_facts() -> None:
    provider, _ = Provider.objects.get_or_create(
        slug="anilist", defaults={"name": "AniList"}
    )
    namespace, _ = ProviderNamespace.objects.get_or_create(
        provider=provider,
        slug="episode",
        defaults={"resource_type": ProviderNamespace.ResourceType.EPISODE},
    )
    episode_entity, observation = _observed_episode_entity(namespace=namespace)
    knowledge_ingestion_service.record_fact(
        entity=episode_entity,
        observation=observation,
        slug="episode-number",
        name="Episode Number",
        value="1",
        value_type="string",
        json_pointer="/episode/number",
    )

    output = _run("backfill_anilist_episode_types")
    assert "[dry-run] episodes=1 linkable=1 unlinked=0" in output
    assert not episode_entity.facts.filter(predicate__slug="episode-type").exists()

    output = _run("backfill_anilist_episode_types", apply=True)
    assert "[applied] episodes=1 linkable=1 unlinked=0" in output
    assert episode_entity.facts.filter(
        predicate__slug="episode-type", value="EP"
    ).exists()


def test_audit_relation_drift_handles_empty_and_populated_sets() -> None:
    empty = _run("audit_relation_drift", limit=5)
    assert empty.startswith("audited=0")

    provider, _ = Provider.objects.get_or_create(
        slug="bangumi", defaults={"name": "Bangumi"}
    )
    subject_ns, _ = ProviderNamespace.objects.get_or_create(
        provider=provider,
        slug="subject",
        defaults={"resource_type": ProviderNamespace.ResourceType.SUBJECT},
    )
    relation_ns, _ = ProviderNamespace.objects.get_or_create(
        provider=provider,
        slug="subject-relations",
        defaults={"resource_type": ProviderNamespace.ResourceType.COLLECTION},
    )
    record = ProviderRecord.objects.create(
        namespace=relation_ns, external_id="100", origin="api", status="active"
    )
    ProviderRecord.objects.create(
        namespace=subject_ns, external_id="100", origin="api", status="active"
    )

    populated = _run("audit_relation_drift", limit=5)
    assert populated.startswith("audited=1")
    assert str(record.id) in populated or "affected=0" in populated


def test_sync_campaign_command_reports_status() -> None:
    from types import SimpleNamespace

    fake = SimpleNamespace(
        pk="00000000-0000-0000-0000-000000000001",
        provider_slug="vndb",
        status="completed",
    )
    with (
        patch(
            "apps.sync.management.commands.sync_campaign.sync_campaign_service"
        ) as service,
        patch(
            "apps.sync.management.commands.sync_campaign.campaign_idempotency_key",
            return_value="key-1",
        ),
    ):
        service.create_campaign.return_value = fake
        service.run.return_value = fake
        output = _run(
            "sync_campaign",
            "vndb",
            ai_mode="off",
            idempotency_key="key-1",
            max_pages=2,
            discovery_pages_per_step=1,
        )

    assert "Campaign 00000000-0000-0000-0000-000000000001 vndb: completed" in output
    created_params = service.create_campaign.call_args.kwargs["parameters"]
    assert created_params["max_pages"] == 2
    assert created_params["discovery_pages_per_step"] == 1


def test_incremental_sync_status_reports_task_states() -> None:
    output = _run("incremental_sync", status=True)

    assert "incremental_subject" in output
    assert "incremental_character" in output
