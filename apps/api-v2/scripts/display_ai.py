"""Propose with the model and compare it with the rule generator."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from uuid import UUID

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from api.contexts.identity.resolution import cluster_ids, resolve
from api.contexts.presentation.agent import propose_with_model
from api.contexts.presentation.bundle import build_bundle
from api.contexts.presentation.display import submit, validate
from api.contexts.presentation.rules import propose


async def run(entity_id: str, language: str, apply: bool) -> int:
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
        bundle = result["bundle"]
        rule = propose(bundle)
        model, usage = await propose_with_model(bundle)
        output = {
            "entity": str(root),
            "input_hash": result["input_hash"],
            "rule": {
                "title_name_id": rule.title_name_id,
                "description_chars": len(rule.description_text),
                "errors": validate(bundle, rule, language=language),
            },
            "model": {
                "title_name_id": model.title_name_id,
                "description_chars": len(model.description_text),
                "errors": validate(bundle, model, language=language),
                "text": model.description_text,
            },
            "same_title": rule.title_name_id == model.title_name_id,
            "usage": usage,
        }
        if apply:
            errors = validate(bundle, model, language=language)
            row_id, state = await submit(
                session,
                bundle=bundle,
                proposal=model,
                input_hash=result["input_hash"],
                model="deepseek-flash",
                prompt_version="display-v1",
            )
            output["stored"] = {"id": row_id, "state": state, "valid": not errors}
            await session.commit()
    await engine.dispose()
    print(json.dumps(output, ensure_ascii=False, default=str))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("entity_id")
    parser.add_argument("--language", default="")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    return asyncio.run(run(args.entity_id, args.language, args.apply))


if __name__ == "__main__":
    sys.exit(main())
