"""Run the ingest cycle against the real schema and roll it back.

The write paths (`record_payload`, `record_observation`) had never been executed — the SQL
was checked column by column, but never run. This script runs the whole cycle inside one
transaction against an existing provider namespace, asserts what the four tables should
hold, checks that a second identical observation deduplicates, and then rolls back. It
leaves no rows behind, which is why it is safe to point at production.

    DATABASE_URL=... python scripts/verify_ingestion.py
"""

from __future__ import annotations

import asyncio
import sys
import uuid

from api.contexts.presentation.fragments import fetch
from api.worker import ingestion, records
from api.worker.session import _sessions

PROVIDER = "vndb"
NAMESPACE = "vn"
RESOURCE_TYPE = "subject"


async def main() -> int:
    external_id = f"probe-{uuid.uuid4().hex[:12]}"
    payload = {"id": external_id, "title": "ingest probe", "probe": True}
    failures: list[str] = []

    async with _sessions() as session:
        try:
            written = await records.record_payload(
                session,
                provider_slug=PROVIDER,
                namespace_slug=NAMESPACE,
                resource_type=RESOURCE_TYPE,
                external_id=external_id,
                payload=payload,
                schema_version="probe-v1",
                canonical_url=f"https://example.invalid/{external_id}",
                origin="probe",
            )
            print(
                f"record_payload: changed={written.changed} "
                f"record={written.record_id} revision={written.revision_id}"
            )
            if not written.changed:
                failures.append("a first write must report changed=True")

            again = await records.record_payload(
                session,
                provider_slug=PROVIDER,
                namespace_slug=NAMESPACE,
                resource_type=RESOURCE_TYPE,
                external_id=external_id,
                payload=payload,
                schema_version="probe-v1",
                origin="probe",
            )
            print(f"record_payload again: changed={again.changed}")
            if again.changed:
                failures.append("an identical payload must not create a revision")
            if again.revision_id != written.revision_id:
                failures.append("the same payload must resolve to the same revision")

            observation_id = await ingestion.record_observation(
                session,
                provider_record_id=written.record_id,
                mapper="probe-mapper",
                mapper_version="v1",
                normalized_data={"title": "ingest probe"},
                schema_name="probe",
                schema_version="probe-v1",
            )
            second = await ingestion.record_observation(
                session,
                provider_record_id=written.record_id,
                mapper="probe-mapper",
                mapper_version="v1",
                normalized_data={"title": "ingest probe"},
                schema_name="probe",
                schema_version="probe-v1",
            )
            print(f"record_observation: {observation_id} then {second}")
            if observation_id != second:
                failures.append("an identical observation must not create a second row")

            rows = await fetch(
                session,
                """
                SELECT
                  (SELECT count(*) FROM provider_observation
                    WHERE id = :observation) AS observations,
                  (SELECT count(*) FROM mapping_run WHERE id = (
                     SELECT mapping_run_id FROM provider_observation WHERE id = :observation
                  )) AS runs,
                  (SELECT count(*) FROM provider_current_observation
                    WHERE provider_record_id = :record
                      AND observation_id = :observation) AS current,
                  (SELECT count(*) FROM provider_observation WHERE id = :observation
                    AND origin = 'mapped' AND normalized_hash IS NOT NULL) AS shaped
                """,
                {"observation": observation_id, "record": written.record_id},
            )
            seen = rows[0]
            print(
                f"observation={seen.observations} mapping_run={seen.runs} "
                f"current={seen.current} mapped+hash={seen.shaped}"
            )
            for label, value in (
                ("observation row", seen.observations),
                ("mapping run", seen.runs),
                ("current observation", seen.current),
                ("origin and hash", seen.shaped),
            ):
                if value != 1:
                    failures.append(f"{label} should be exactly 1, saw {value}")
        finally:
            await session.rollback()
            print("rolled back: no rows were kept")

    if failures:
        for failure in failures:
            print(f"FAIL {failure}")
        return 1
    print("OK the ingest cycle behaves as specified")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
