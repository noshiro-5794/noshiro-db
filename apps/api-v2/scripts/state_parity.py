"""Compare a mutating request by the state it leaves, not by its answer.

Two calls to the same write endpoint cannot both start from the same rows, so the
responses differ for reasons that have nothing to do with the port. This runs the
request against one service, snapshots the rows it touched, restores the seed and
runs it against the other — then compares both the responses and the snapshots.

    uv run python -m scripts.state_parity --old ... --new ... \
        --setup "insert into t ..." --snapshot "select * from t" \
        --cleanup "delete from t ..." --method PUT --path /api/v1/...
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from typing import Any

import asyncpg

from scripts.parity import DEFAULT_HEADERS, diff, fetch, normalize


async def _sql(dsn: str, statement: str) -> list[dict[str, Any]]:
    connection = await asyncpg.connect(dsn)
    try:
        # A seed often needs more than one statement; asyncpg prepares one at a
        # time, so they are split here.
        rows = []
        for part in [item.strip() for item in statement.split(";") if item.strip()]:
            rows = await connection.fetch(part)
    finally:
        await connection.close()
    return [dict(row) for row in rows]


def _dsn() -> str:
    dsn = os.environ.get("DATABASE_URL", "")
    if not dsn:
        raise SystemExit("DATABASE_URL is required")
    return dsn


async def _call(
    base: str, path: str, headers: dict[str, str], timeout: float, method: str, body: str | None
) -> tuple[int, Any]:
    return await asyncio.to_thread(fetch, base, path, headers, timeout, method, body)


async def run(args: argparse.Namespace) -> int:
    headers = dict(DEFAULT_HEADERS)
    if args.body is not None:
        headers["Content-Type"] = "application/json"
    for header in args.header:
        key, _, value = header.partition(":")
        headers[key.strip()] = value.strip()

    dsn = _dsn()
    results = {}
    for name, base in (("old", args.old), ("new", args.new)):
        await _sql(dsn, args.cleanup)
        await _sql(dsn, args.setup)
        status, body = await _call(base, args.path, headers, args.timeout, args.method, args.body)
        state = await _sql(dsn, args.snapshot)
        results[name] = {"status": status, "body": body, "state": state}
        await _sql(dsn, args.cleanup)

    differences = list(
        diff(
            normalize(results["old"], unordered=frozenset(args.unordered)),
            normalize(results["new"], unordered=frozenset(args.unordered)),
            ignore=frozenset(args.ignore),
        )
    )
    if differences:
        print(f"FAIL {args.path}")
        for line in differences[:20]:
            print(f"  {line}")
        return 1
    print(f"OK   {args.path} — response and state match")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old", required=True)
    parser.add_argument("--new", required=True)
    parser.add_argument("--path", required=True)
    parser.add_argument("--method", default="PUT")
    parser.add_argument("--body", default=None)
    parser.add_argument("--header", action="append", default=[])
    parser.add_argument("--setup", required=True)
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--cleanup", required=True)
    parser.add_argument("--unordered", action="append", default=[])
    parser.add_argument("--ignore", action="append", default=[])
    parser.add_argument("--timeout", type=float, default=60.0)
    return asyncio.run(run(parser.parse_args(argv)))


if __name__ == "__main__":
    sys.exit(main())
