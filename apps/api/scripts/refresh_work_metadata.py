"""List or refresh a bounded page of work records missing the current field mapping."""

import argparse
import asyncio
import json

from api.db import fetch
from api.worker import anilist_import, campaign_imports, mal_import, subject_import, vndb_projection
from api.worker.session import session_scope

MAPPERS = {
    "anilist": ("anime", anilist_import.MAPPER_VERSION),
    "mal": ("anime", mal_import.MAPPER_VERSION),
    "bangumi": ("subject", subject_import.MAPPER_VERSION),
    "vndb": ("vn", vndb_projection.WORK_MAPPER_VERSION),
}


async def ignore_progress(_message: str, _total: int | None) -> None:
    pass


async def run(args: argparse.Namespace) -> None:
    namespace, version = MAPPERS[args.provider]
    async with session_scope() as session:
        rows = await fetch(
            session,
            """
            SELECT record.external_id
            FROM provider_record AS record
            JOIN provider_namespace AS namespace ON namespace.id = record.namespace_id
            JOIN provider ON provider.id = namespace.provider_id
            JOIN entity_representation AS representation
              ON representation.provider_record_id = record.id
              AND representation.is_active
            JOIN work ON work.entity_id = representation.entity_id
            WHERE provider.slug = :provider AND namespace.slug = :namespace
              AND provider.is_enabled AND provider.storage_policy <> 'forbidden'
              AND record.status = 'active' AND record.external_id > :after
              AND work.work_type IN ('anime','galgame')
              AND NOT EXISTS (
                  SELECT 1 FROM mapping_run AS mapping
                  WHERE mapping.revision_id = record.latest_revision_id
                    AND mapping.mapper_version = :version AND mapping.status = 'succeeded'
              )
            GROUP BY record.external_id
            ORDER BY record.external_id
            LIMIT :limit
            """,
            {
                "provider": args.provider,
                "namespace": namespace,
                "version": version,
                "after": args.after,
                "limit": args.limit,
            },
        )
    identifiers = [row.external_id for row in rows]
    print(
        json.dumps(
            {
                "provider": args.provider,
                "external_ids": identifiers,
                "next_cursor": identifiers[-1] if identifiers else None,
            }
        ),
        flush=True,
    )
    if not args.apply:
        return
    for identifier in identifiers:
        payload = await campaign_imports.fetch_source(
            args.provider, identifier, forbidden=False, progress=ignore_progress
        )
        async with session_scope() as session:
            await campaign_imports.project_source(session, args.provider, identifier, payload)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("provider", choices=MAPPERS)
    parser.add_argument("--after", default="")
    parser.add_argument("--limit", type=int, choices=range(1, 501), default=20, metavar="1-500")
    parser.add_argument(
        "--apply", action="store_true", help="Fetch and reproject the selected page."
    )
    asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    main()
