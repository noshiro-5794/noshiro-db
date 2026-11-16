"""Capture what the old matcher produced, so a port can be compared against it.

The matching engine cannot be verified by diffing rows written inside one transaction: its
output is a *set* of candidates with scores, and correctness means "the same set with the
same scores". So the first step is a read-only baseline — totals by policy and status, a
bounded sample of scored pairs, and a digest over that sample.

    DATABASE_URL=... python scripts/capture_matching_baseline.py --out baseline.json

The digest makes the comparison one line: re-run the port, capture the same way, and the
two digests either match or they do not.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json

from api.contexts.presentation.fragments import fetch
from api.worker.session import session_scope

BY_POLICY = """
SELECT policy_version, status, count(*) AS c
FROM match_candidate
GROUP BY policy_version, status
ORDER BY policy_version, status
"""

SAMPLE = """
SELECT id, left_entity_id, right_entity_id, score::text AS score,
       runner_up_margin::text AS margin, policy_version, status
FROM match_candidate
ORDER BY policy_version, left_entity_id, right_entity_id
LIMIT :limit
"""


def digest_of(rows: list[dict[str, str]]) -> str:
    payload = json.dumps(rows, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


async def capture(limit: int) -> dict[str, object]:
    async with session_scope() as session:
        totals = await fetch(session, BY_POLICY, {})
        rows = await fetch(session, SAMPLE, {"limit": limit})
        sample = [
            {
                "left": str(row.left_entity_id),
                "right": str(row.right_entity_id),
                "score": row.score,
                "margin": row.margin,
                "policy": row.policy_version,
                "status": row.status,
            }
            for row in rows
        ]
    return {
        "totals": [
            {"policy": row.policy_version, "status": row.status, "count": row.c} for row in totals
        ],
        "sample_size": len(sample),
        "sample_digest": digest_of(sample),
        "sample": sample,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--out", default="")
    args = parser.parse_args()
    result = asyncio.run(capture(args.limit))
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(text)
        print(
            f"wrote {args.out}: {result['sample_size']} sampled, digest {result['sample_digest'][:16]}"
        )
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
