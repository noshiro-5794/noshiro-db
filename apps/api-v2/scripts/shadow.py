"""Sample entities and compare every implemented endpoint between the services.

`parity.py` checks the paths you name. This samples them: a random set of public
entities is run through each endpoint on both services, and the run reports how
many comparisons matched. Order-insensitive endpoints are compared as sets, the
same way the single-path tool does it.

    uv run python scripts/shadow.py --old http://127.0.0.1:8008 \
        --new http://127.0.0.1:8010 --count 20
"""

from __future__ import annotations

import argparse
import asyncio
import os
import random
import sys

import asyncpg

from scripts.parity import DEFAULT_HEADERS, diff, fetch, normalize

# (suffix, ordered) — `ordered=False` means Django returns the list without an
# ORDER BY, so the comparison sorts it before diffing.
ENDPOINTS: tuple[tuple[str, bool], ...] = (
    ("", True),
    ("/metrics/", True),
    ("/characters/?page_size=8", True),
    ("/episodes/?page_size=8", True),
    ("/relations/", False),
    ("/credits/", False),
    ("/releases/", False),
    ("/evidence/", False),
)

IGNORE = frozenset({"trace_id", "next", "previous"})


async def sample_ids(dsn: str, count: int) -> list[str]:
    connection = await asyncpg.connect(dsn)
    try:
        rows = await connection.fetch(
            """
            SELECT id FROM entity
            WHERE lifecycle = 'active' AND visibility = 'public'
            ORDER BY random() LIMIT $1
            """,
            count,
        )
    finally:
        await connection.close()
    return [str(row["id"]) for row in rows]


def unordered_paths(ordered: bool) -> frozenset[str]:
    paths = {"facts[].evidence"}
    if not ordered:
        paths.add("$")
    return frozenset(paths)


async def compare(
    *, old: str, new: str, entity_id: str, suffix: str, ordered: bool, timeout: float
) -> tuple[bool, str]:
    path = f"/api/v1/index/entities/{entity_id}{suffix}"
    try:
        old_status, expected = await asyncio.to_thread(fetch, old, path, DEFAULT_HEADERS, timeout)
        new_status, actual = await asyncio.to_thread(fetch, new, path, DEFAULT_HEADERS, timeout)
    except Exception as error:
        return False, f"FAIL {path}: {error}"
    if old_status != new_status:
        return False, f"FAIL {path}: status {old_status} != {new_status}"
    ignored = unordered_paths(ordered)
    differences = list(
        diff(
            normalize(expected, unordered=ignored),
            normalize(actual, unordered=ignored),
            ignore=IGNORE,
        )
    )
    if differences:
        return False, f"FAIL {path}\n  " + "\n  ".join(differences[:5])
    return True, path


async def run(*, old: str, new: str, count: int, timeout: float) -> int:
    dsn = os.environ.get("DATABASE_URL", "")
    if not dsn:
        print("DATABASE_URL is required to sample entities", file=sys.stderr)
        return 2
    ids = await sample_ids(dsn, count)
    random.shuffle(ids)
    passed = failed = 0
    for entity_id in ids:
        for suffix, ordered in ENDPOINTS:
            ok, message = await compare(
                old=old,
                new=new,
                entity_id=entity_id,
                suffix=suffix,
                ordered=ordered,
                timeout=timeout,
            )
            if ok:
                passed += 1
            else:
                failed += 1
                print(message)
    total = passed + failed
    print(f"\n{passed}/{total} comparisons matched ({len(ids)} entities)")
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old", required=True)
    parser.add_argument("--new", required=True)
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--timeout", type=float, default=120.0)
    args = parser.parse_args(argv)
    return asyncio.run(run(old=args.old, new=args.new, count=args.count, timeout=args.timeout))


if __name__ == "__main__":
    sys.exit(main())
