"""Reverse a reviewed identity match while retaining its source and user records."""

import argparse
import asyncio
from uuid import UUID

from api.contexts.index.resolution import split
from api.worker.session import session_scope


async def run(merge_event_id: UUID, reason: str) -> None:
    async with session_scope() as session:
        identifier = await split(session, merge_event_id=merge_event_id, reason=reason)
    print(identifier)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("merge_event_id", type=UUID)
    parser.add_argument("--reason", required=True)
    args = parser.parse_args()
    asyncio.run(run(args.merge_event_id, args.reason))


if __name__ == "__main__":
    main()
