from unittest.mock import AsyncMock

import pytest

from api.contexts.identity import vndb
from api.contexts.index import resolution
from api.contexts.ingestion import entities, facts, records
from api.contexts.ingestion import observations as ingestion
from api.db import fetch
from api.integrations.providers.vndb import VNDBImportBatch
from api.worker.vndb_import import import_batch


async def bangumi_reference(session, work_type="game"):
    await fetch(
        session,
        """
        INSERT INTO provider
          (slug, name, base_url, terms_url, attribution_url, license_name,
           storage_policy, redistribution_policy, commercial_use_policy,
           ai_usage_policy, is_enabled, created_at, updated_at)
        SELECT 'bangumi', 'Bangumi', base_url, terms_url, attribution_url, license_name,
               storage_policy, redistribution_policy, commercial_use_policy,
               ai_usage_policy, is_enabled, now(), now() FROM provider WHERE slug='vndb'
        RETURNING id
        """,
        {},
    )
    recorded = await records.record_payload(
        session,
        provider_slug="bangumi",
        namespace_slug="subject",
        resource_type="subject",
        external_id="1",
        payload={"id": 1, "vndb": "v1"},
    )
    observed = await ingestion.record_observation(
        session,
        provider_record_id=recorded.record_id,
        mapper="bangumi.subject",
        mapper_version="test",
        normalized_data={"id": 1, "vndb": "v1"},
        schema_name="index.work",
        schema_version="1",
    )
    work = await entities.map_work(
        session,
        provider_record_id=recorded.record_id,
        mapped_data={"subject_type": work_type},
    )
    await facts.record_fact(
        session,
        entity_id=work.entity_id,
        observation_id=observed,
        slug="external-id-vndb",
        name="VNDB ID",
        value="v1",
        value_type="string",
        json_pointer="/vndb",
    )
    return work.entity_id, observed


@pytest.mark.asyncio
async def test_explicit_current_identifier_binds_once_and_keeps_source_representations(
    vndb_session,
):
    session = vndb_session
    bangumi_id, _ = await bangumi_reference(session)
    entity_id = await import_batch(session, "v1", VNDBImportBatch(work={"id": "v1", "title": "VN"}))
    assert await resolution.resolve(session, bangumi_id) == entity_id
    assert (
        await import_batch(session, "v1", VNDBImportBatch(work={"id": "v1", "title": "VN"}))
        == entity_id
    )
    decisions = await fetch(session, "SELECT outcome, decided_by FROM candidate_decision", {})
    assert [tuple(row) for row in decisions] == [("bind", "official_external_id")]
    assert (
        await fetch(
            session, "SELECT count(*) AS n FROM entity_identity_membership WHERE is_active", {}
        )
    )[0].n == 1
    assert (
        await fetch(session, "SELECT count(*) AS n FROM entity_representation WHERE is_active", {})
    )[0].n == 2


@pytest.mark.asyncio
async def test_incompatible_official_identifier_records_abstention(vndb_session):
    session = vndb_session
    bangumi_id, _ = await bangumi_reference(session, "anime")
    entity_id = await import_batch(session, "v1", VNDBImportBatch(work={"id": "v1"}))
    assert entity_id != bangumi_id
    decisions = await fetch(session, "SELECT outcome FROM candidate_decision", {})
    assert [row.outcome for row in decisions] == ["abstain"]
    assert (await fetch(session, "SELECT hard_conflicts FROM match_candidate", {}))[
        0
    ].hard_conflicts == ["entity_type"]


@pytest.mark.asyncio
async def test_superseded_identifier_cannot_bind_a_work(vndb_session):
    session = vndb_session
    bangumi_id, observed = await bangumi_reference(session)
    await fetch(
        session,
        "DELETE FROM provider_current_observation WHERE observation_id=:id RETURNING id",
        {"id": observed},
    )
    entity_id = await import_batch(session, "v1", VNDBImportBatch(work={"id": "v1"}))
    assert entity_id != bangumi_id
    assert (await fetch(session, "SELECT count(*) AS n FROM match_candidate", {}))[0].n == 0


@pytest.mark.asyncio
async def test_refused_identity_merge_falls_back_to_one_durable_abstention(
    vndb_session, monkeypatch
):
    session = vndb_session
    await bangumi_reference(session)
    monkeypatch.setattr(
        resolution,
        "merge",
        AsyncMock(side_effect=resolution.UserLibraryConflict("existing libraries")),
    )
    entity_id = await import_batch(session, "v1", VNDBImportBatch(work={"id": "v1"}))
    assert await vndb.reconcile(session, entity_id, "v1") == entity_id
    decisions = await fetch(session, "SELECT outcome FROM candidate_decision", {})
    assert [row.outcome for row in decisions] == ["abstain"]
