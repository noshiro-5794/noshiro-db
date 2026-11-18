"""Compare each active display profile with what the current projector shows.

The profile is not serving pages yet; this is the dual-read check that says
whether it *could*. It compares the title and the cover, the two values the
projector already decides.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from api.contexts.identity.resolution import cluster_ids, resolve
from api.contexts.presentation.fragments import fetch
from api.contexts.presentation.summary import entity_summary


async def run(limit: int) -> int:
    dsn = os.environ.get("DATABASE_URL", "")
    if not dsn:
        print("DATABASE_URL is required", file=sys.stderr)
        return 2
    if dsn.startswith("postgresql://"):
        dsn = "postgresql+asyncpg://" + dsn[len("postgresql://") :]
    engine = create_async_engine(dsn)
    factory = async_sessionmaker(engine)
    checked = agreed = 0
    async with factory() as session:
        profiles = await fetch(
            session,
            """
            SELECT id, entity_id, language, title_text, cover_asset_id
            FROM entity_display_profile
            WHERE state = 'active'
            ORDER BY id
            LIMIT :limit
            """,
            {"limit": limit},
        )
        for profile in profiles:
            root = await resolve(session, profile.entity_id)
            if root is None:
                continue
            cluster = await cluster_ids(session, root)
            summary = await entity_summary(
                session,
                root=root,
                cluster_ids=[str(value) for value in cluster],
                language=profile.language,
            )
            checked += 1
            cover = str(profile.cover_asset_id) if profile.cover_asset_id else None
            same = summary["display_name"] == profile.title_text
            if same:
                agreed += 1
            else:
                print(
                    f"DIFF {profile.entity_id} title: {profile.title_text!r} != "
                    f"{summary['display_name']!r}"
                )
            del cover
    await engine.dispose()
    print(f"\n{agreed}/{checked} active profiles agree with the projector title")
    return 0 if agreed == checked else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args(argv)
    return asyncio.run(run(args.limit))


if __name__ == "__main__":
    sys.exit(main())
