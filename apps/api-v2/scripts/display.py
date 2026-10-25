"""Propose a display profile for one entity with the rule generator.

Without `--apply` it only prints what would be proposed and whether it validates;
with `--apply` it stores the draft (or the rejection) in `entity_display_profile`.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from dataclasses import asdict
from uuid import UUID

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from api.contexts.identity.resolution import cluster_ids, resolve
from api.contexts.presentation.bundle import build_bundle
from api.contexts.presentation.display import activate, submit, validate
from api.contexts.presentation.rules import propose


async def run(entity_id: str, language: str, apply: bool, do_activate: bool = False) -> int:
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
        proposal = propose(result["bundle"])
        errors = validate(result["bundle"], proposal, language=language)
        output: dict[str, object] = {
            "entity": str(root),
            "input_hash": result["input_hash"],
            "errors": errors,
            "proposal": asdict(proposal),
        }
        if apply:
            row_id, state = await submit(
                session,
                bundle=result["bundle"],
                proposal=proposal,
                input_hash=result["input_hash"],
                model="rules",
                prompt_version="rules-v1",
            )
            output["stored"] = {"id": row_id, "state": state}
            if do_activate and state == "draft":
                active_id = await activate(
                    session,
                    entity_id=root,
                    language=language,
                    input_hash=result["input_hash"],
                )
                output["activated"] = active_id
            await session.commit()
    await engine.dispose()
    print(json.dumps(output, ensure_ascii=False, default=str))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("entity_id")
    parser.add_argument("--language", default="")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--activate", action="store_true")
    args = parser.parse_args(argv)
    return asyncio.run(
        run(args.entity_id, args.language, args.apply or args.activate, args.activate)
    )


if __name__ == "__main__":
    sys.exit(main())
