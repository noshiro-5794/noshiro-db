"""Print the display bundle for one entity, as the generator would receive it."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from uuid import UUID

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from api.contexts.identity.resolution import cluster_ids, resolve
from api.contexts.presentation.bundle import build_bundle


async def run(entity_id: str, language: str) -> int:
    dsn = os.environ.get("DATABASE_URL", "")
    if not dsn:
        print("DATABASE_URL is required", file=sys.stderr)
        return 2
    if dsn.startswith("postgresql://"):
        dsn = "postgresql+asyncpg://" + dsn[len("postgresql://") :]
    engine = create_async_engine(dsn)
    factory = async_sessionmaker(engine)
    async with factory() as session:
        root = await resolve(session, UUID(entity_id))
        if root is None:
            print(f"unknown entity: {entity_id}", file=sys.stderr)
            return 1
        cluster = await cluster_ids(session, root)
        result = await build_bundle(
            session,
            root=root,
            cluster_ids=[str(value) for value in cluster],
            language=language,
        )
    await engine.dispose()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("entity_id")
    parser.add_argument("--language", default="")
    args = parser.parse_args(argv)
    return asyncio.run(run(args.entity_id, args.language))


if __name__ == "__main__":
    sys.exit(main())
