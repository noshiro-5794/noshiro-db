"""Replay a captured Bangumi subject through the current catalogue mapper."""

import argparse
import asyncio
from uuid import UUID

from api.worker.session import session_scope
from api.worker.subject_import import replay_subject


async def replay(subject_id: int, fetch_id: UUID) -> None:
    async with session_scope() as session:
        entity_id = await replay_subject(session, subject_id, fetch_id)
    print(entity_id)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("subject_id", type=int)
    parser.add_argument("fetch_id", type=UUID)
    args = parser.parse_args()
    asyncio.run(replay(args.subject_id, args.fetch_id))


if __name__ == "__main__":
    main()
