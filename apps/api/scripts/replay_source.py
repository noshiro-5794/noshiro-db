"""Replay catalogue captures without contacting provider APIs."""

import argparse
import asyncio
import json
from uuid import UUID

from api.worker.session import session_scope
from api.worker.source_replay import replay_batch
from api.worker.subject_import import replay_subject


async def replay(args: argparse.Namespace) -> None:
    async with session_scope() as session:
        if args.command == "batch":
            entity_id = await replay_batch(session, args.batch_id, apply=args.apply)
            result = {"entity_id": str(entity_id), "applied": args.apply}
        else:
            entity_id = await replay_subject(session, args.subject_id, args.fetch_id)
            result = {"entity_id": str(entity_id), "applied": True}
    print(json.dumps(result))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    batch = commands.add_parser("batch", help="Replay a complete captured import.")
    batch.add_argument("batch_id", type=UUID)
    batch.add_argument("--apply", action="store_true", help="Keep a current batch's projections.")
    subject = commands.add_parser("bangumi-subject", help="Apply a standalone subject response.")
    subject.add_argument("subject_id", type=int)
    subject.add_argument("fetch_id", type=UUID)
    asyncio.run(replay(parser.parse_args()))


if __name__ == "__main__":
    main()
