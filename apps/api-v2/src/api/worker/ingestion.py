"""Recording what a provider told us, once per revision and mapper.

Ported from `KnowledgeIngestionService.record_observation`. The shape of the guarantee:

* The same payload, from the same revision, through the same mapper, is recorded **once**.
  The lookup is by ``normalized_hash`` so a re-run costs a read, not a new row.
* Every genuinely new observation gets its own ``mapping_run`` row, because the run is the
  record of "this mapper processed this revision" — the audit trail, not a counter.
* The ``provider_current_observation`` row is the projection the read paths use, so it is
  updated to the observation just recorded.

The hash is over a canonical JSON rendering: sorted keys, no whitespace, non-JSON values
stringified. If that ever changes, every stored hash stops matching and the whole catalogue
is re-ingested, so the function is tested directly.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.presentation.fragments import fetch

LEGACY_ORIGIN = "legacy"
MAPPED_ORIGIN = "mapped"


def normalized_hash(data: Any) -> str:
    """Stable digest of a payload, independent of key order and whitespace."""
    encoded = json.dumps(
        data,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        default=str,
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


async def _latest_revision(session: AsyncSession, provider_record_id: Any) -> Any:
    rows = await fetch(
        session,
        "SELECT latest_revision_id FROM provider_record WHERE id = :id",
        {"id": provider_record_id},
    )
    if not rows:
        raise LookupError(f"provider_record {provider_record_id} does not exist")
    return rows[0].latest_revision_id


async def _select_current(
    session: AsyncSession,
    *,
    provider_record_id: Any,
    mapper: str,
    schema_name: str,
    observation_id: Any,
) -> None:
    await fetch(
        session,
        """
        INSERT INTO provider_current_observation
          (provider_record_id, mapper, schema_name, observation_id, created_at, updated_at)
        VALUES (:record, :mapper, :schema, :observation, now(), now())
        ON CONFLICT (provider_record_id, mapper, schema_name) DO UPDATE
          SET observation_id = EXCLUDED.observation_id, updated_at = now()
        RETURNING id
        """,
        {
            "record": provider_record_id,
            "mapper": mapper,
            "schema": schema_name,
            "observation": observation_id,
        },
    )


async def record_observation(
    session: AsyncSession,
    *,
    provider_record_id: Any,
    mapper: str,
    mapper_version: str,
    normalized_data: dict[str, Any],
    schema_name: str,
    schema_version: str,
    observed_at: datetime | None = None,
) -> Any:
    """Record an observation and return its id."""
    digest = normalized_hash(normalized_data)
    payload = json.dumps(normalized_data, ensure_ascii=False, default=str)
    at = observed_at or datetime.now(UTC)
    revision_id = await _latest_revision(session, provider_record_id)

    if revision_id is None:
        # A record with no revision predates the revision pipeline; it can only carry
        # one legacy observation per distinct payload.
        rows = await fetch(
            session,
            """
            SELECT id FROM provider_observation
            WHERE provider_record_id = :record AND mapping_run_id IS NULL
              AND schema_name = :schema AND normalized_hash = :hash
            LIMIT 1
            """,
            {"record": provider_record_id, "schema": schema_name, "hash": digest},
        )
        if rows:
            observation_id = rows[0].id
        else:
            inserted = await fetch(
                session,
                """
                INSERT INTO provider_observation
                  (provider_record_id, mapping_run_id, origin, schema_name,
                   schema_version, normalized_data, normalized_hash, observed_at,
                   created_at, updated_at)
                VALUES (:record, NULL, :origin, :schema, :version,
                        CAST(:data AS jsonb), :hash, :at, now(), now())
                RETURNING id
                """,
                {
                    "record": provider_record_id,
                    "origin": LEGACY_ORIGIN,
                    "schema": schema_name,
                    "version": schema_version,
                    "data": payload,
                    "hash": digest,
                    "at": at,
                },
            )
            observation_id = inserted[0].id
        await _select_current(
            session,
            provider_record_id=provider_record_id,
            mapper=mapper,
            schema_name=schema_name,
            observation_id=observation_id,
        )
        return observation_id

    existing = await fetch(
        session,
        """
        SELECT o.id
        FROM provider_observation AS o
        JOIN mapping_run AS r ON r.id = o.mapping_run_id
        WHERE o.provider_record_id = :record AND r.revision_id = :revision
          AND r.mapper = :mapper AND r.mapper_version = :mapper_version
          AND r.status = 'succeeded' AND o.schema_name = :schema
          AND o.normalized_hash = :hash
        LIMIT 1
        """,
        {
            "record": provider_record_id,
            "revision": revision_id,
            "mapper": mapper,
            "mapper_version": mapper_version,
            "schema": schema_name,
            "hash": digest,
        },
    )
    if existing:
        await _select_current(
            session,
            provider_record_id=provider_record_id,
            mapper=mapper,
            schema_name=schema_name,
            observation_id=existing[0].id,
        )
        return existing[0].id

    run = await fetch(
        session,
        """
        INSERT INTO mapping_run
          (revision_id, mapper, mapper_version, status, started_at, created_at, updated_at)
        VALUES (:revision, :mapper, :mapper_version, 'running', now(), now(), now())
        RETURNING id
        """,
        {
            "revision": revision_id,
            "mapper": mapper,
            "mapper_version": mapper_version,
        },
    )
    run_id = run[0].id
    inserted = await fetch(
        session,
        """
        INSERT INTO provider_observation
          (provider_record_id, mapping_run_id, origin, schema_name, schema_version,
           normalized_data, normalized_hash, observed_at, created_at, updated_at)
        VALUES (:record, :run, :origin, :schema, :version, CAST(:data AS jsonb),
                :hash, :at, now(), now())
        RETURNING id
        """,
        {
            "record": provider_record_id,
            "run": run_id,
            "origin": MAPPED_ORIGIN,
            "schema": schema_name,
            "version": schema_version,
            "data": payload,
            "hash": digest,
            "at": at,
        },
    )
    observation_id = inserted[0].id
    await fetch(
        session,
        "UPDATE mapping_run SET status = 'succeeded', finished_at = now(),"
        " updated_at = now() WHERE id = :id RETURNING id",
        {"id": run_id},
    )
    await _select_current(
        session,
        provider_record_id=provider_record_id,
        mapper=mapper,
        schema_name=schema_name,
        observation_id=observation_id,
    )
    return observation_id


__all__ = ["LEGACY_ORIGIN", "MAPPED_ORIGIN", "normalized_hash", "record_observation"]
