from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command

from apps.index.models import (
    Entity,
    EntityName,
    Provider,
    ProviderNamespace,
    ProviderRecord,
    ProviderRepresentation,
)

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


def test_generate_match_candidates_dry_run_reports_counts() -> None:
    _anilist_entity()

    output = _run("generate_match_candidates", dry_run=True)

    assert "dry-run" in output
    assert "anilist_entities=1" in output
    assert "candidates_created=0" in output


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
