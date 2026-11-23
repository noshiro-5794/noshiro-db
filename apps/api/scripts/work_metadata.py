"""Preview, save, inspect, or publish a work's metadata for one language."""

import argparse
import asyncio
import json
from dataclasses import asdict
from uuid import UUID

from api.contexts.identity.resolution import cluster_ids, resolve
from api.contexts.presentation.bundle import build_bundle
from api.contexts.presentation.display import activate, submit, validate
from api.contexts.presentation.rules import propose
from api.db import fetch
from api.worker.session import session_scope


async def run(args: argparse.Namespace) -> None:
    async with session_scope() as session:
        if args.command == "publish":
            identifier = await activate(
                session,
                entity_id=args.entity,
                language=args.language,
                input_hash=args.input_hash,
                reviewed_by=args.reviewer,
            )
            if identifier is None:
                raise SystemExit("No current draft matches this work, language, and evidence hash.")
            print(json.dumps({"published_revision_id": identifier}))
            return
        if args.command == "show":
            revisions = await fetch(
                session,
                """
                SELECT revision.id, revision.title_text, revision.description_text, revision.state,
                       revision.cover_asset_id, revision.input_hash, revision.model,
                       revision.prompt_version, revision.reviewed_by, revision.reviewed_at,
                       publication.published_at
                FROM entity_metadata_revision AS revision
                LEFT JOIN entity_metadata_publication AS publication
                  ON publication.revision_id = revision.id
                WHERE revision.entity_id = :entity AND revision.language = :language
                ORDER BY revision.id DESC LIMIT :limit
                """,
                {"entity": args.entity, "language": args.language, "limit": args.limit},
            )
            print(
                json.dumps(
                    [dict(row._mapping) for row in revisions], default=str, ensure_ascii=False
                )
            )
            return
        root = await resolve(session, args.entity)
        if root is None:
            raise SystemExit("Work not found.")
        result = await build_bundle(
            session,
            root=root,
            cluster_ids=sorted(map(str, await cluster_ids(session, root))),
            language=args.language,
        )
        bundle = result["bundle"]
        if bundle["entity"]["entity_type"] != "work" or not bundle["names"]:
            raise SystemExit("An active work with a current name is required.")
        proposal = propose(bundle)
        output = {
            "entity_id": str(root),
            "input_hash": result["input_hash"],
            "errors": validate(bundle, proposal, language=args.language),
            "proposal": asdict(proposal),
        }
        if args.save:
            identifier, state = await submit(
                session,
                bundle=bundle,
                proposal=proposal,
                input_hash=result["input_hash"],
                model="rules",
                prompt_version="rules-v1",
            )
            output["revision"] = {"id": identifier, "state": state}
        print(json.dumps(output, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    preview = commands.add_parser("propose")
    preview.add_argument("--save", action="store_true")
    show = commands.add_parser("show")
    show.add_argument("--limit", type=int, choices=range(1, 101), default=20, metavar="1-100")
    publish = commands.add_parser("publish")
    publish.add_argument("input_hash")
    publish.add_argument("--reviewer", type=int)
    for command in (preview, show, publish):
        command.add_argument("entity", type=UUID)
        command.add_argument("--language", default="")
    asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    main()
