"""Provenance joins and observation visibility for catalogue read models."""

from __future__ import annotations

from typing import Any

from api.shared.timestamps import isoformat

PROVENANCE = """
    provider.slug AS provider_slug,
    namespace.slug AS namespace_slug,
    record.external_id AS external_id,
    observation.id AS observation_id,
    run.revision_id AS revision_id,
    observation.observed_at AS observed_at
"""

PROVENANCE_JOINS = """
    LEFT JOIN provider_observation AS observation ON observation.id = {observation}
    LEFT JOIN mapping_run AS run ON run.id = observation.mapping_run_id
    LEFT JOIN provider_record AS record ON record.id = {record}
    LEFT JOIN provider_namespace AS namespace ON namespace.id = record.namespace_id
    LEFT JOIN provider AS provider ON provider.id = namespace.provider_id
"""

CURRENT = """
    (
        ({observation} IS NULL AND {record} IS NULL)
        OR (
            {observation} IS NOT NULL
            AND EXISTS (
                SELECT 1
                FROM provider_current_observation AS pointer
                JOIN provider_record AS current_record
                  ON current_record.id = observation.provider_record_id
                JOIN provider_namespace AS current_namespace
                  ON current_namespace.id = current_record.namespace_id
                JOIN provider AS current_provider
                  ON current_provider.id = current_namespace.provider_id
                WHERE pointer.observation_id = {observation}
                  AND pointer.provider_record_id = observation.provider_record_id
                  AND current_record.status = 'active'
                  AND current_provider.redistribution_policy <> 'forbidden'
            )
        )
    )
"""


def row_provenance(row: Any) -> dict[str, Any] | None:
    if row.provider_slug is None:
        return None
    return {
        "provider": row.provider_slug,
        "namespace": row.namespace_slug,
        "external_id": row.external_id,
        "observation_id": str(row.observation_id) if row.observation_id else None,
        "revision_id": str(row.revision_id) if row.revision_id else None,
        "observed_at": isoformat(row.observed_at),
    }


def visible(row: Any, *, content_allowed: bool) -> bool:
    if not content_allowed or row.safety in {"explicit", "suggestive"}:
        return False
    return bool(getattr(row, "spoiler_level", 0) <= 0)


def current_rows(
    *,
    table: str,
    alias: str,
    columns: str,
    record: str,
    extra_join: str = "",
) -> str:
    """A current-row query for a table that carries its own provenance columns.

    ``record`` is where the provenance comes from — the asset's record for a
    cover, the row's own for a name. Whether the row is current is decided by its
    observation, inside ``CURRENT``.
    """
    observation = f"{alias}.observation_id"
    return f"""
        SELECT {columns}, {PROVENANCE}
        FROM {table} AS {alias}
        {extra_join}
        {PROVENANCE_JOINS.format(record=record, observation=observation)}
        WHERE {alias}.entity_id = ANY(CAST(:ids AS uuid[]))
          AND {CURRENT.format(record=record, observation=observation)}
    """
