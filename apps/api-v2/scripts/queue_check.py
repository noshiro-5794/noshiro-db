"""The queues routing writes to must be queues a worker listens on.

They are two independent declarations: `task_routes` in the worker app decides where a
message is published, and the compose command's `-Q` decides what a worker consumes. When
they disagree the message is not lost — it sits on the queue, unread, with no error
anywhere. That is exactly how a task silently stops running.

    python scripts/queue_check.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
APP = REPO / "apps/api-v2/src/api/worker/app.py"
COMPOSE = REPO / "deploy/compose.prod.yml"

ROUTE = re.compile(r'"apps\.[\w.*]+"\s*:\s*\{\s*"queue"\s*:\s*"([\w.-]+)"')
DEFAULT_QUEUE = re.compile(r'task_default_queue\s*=\s*"([\w.-]+)"')
LISTEN = re.compile(r"-Q\s+\$\{API_V2_WORKER_QUEUES:-([\w,.-]+)\}")

# Queues the replacement routes to but does not consume yet, because the Django worker
# still owns those tasks. Listing them here is the point: an unlisted queue that nobody
# listens on is the silent failure this check exists for, so moving a task means moving
# its queue out of this set in the same change.
DURING_MIGRATION = {
    "ai": "the Django ai worker still runs the AI tasks",
}


def routed_queues() -> tuple[set[str], str]:
    text = APP.read_text()
    routed = set(ROUTE.findall(text))
    default = DEFAULT_QUEUE.search(text)
    return routed, (default.group(1) if default else "realtime")


def listened_queues() -> set[str]:
    match = LISTEN.search(COMPOSE.read_text())
    if match is None:
        return set()
    return {q.strip() for q in match.group(1).split(",") if q.strip()}


def main() -> int:
    routed, default = routed_queues()
    listened = listened_queues()
    needed = routed | {default}
    missing = sorted(needed - listened - set(DURING_MIGRATION))
    extra = sorted(listened - needed)
    print(f"routing writes to : {', '.join(sorted(needed))}")
    print(f"worker listens on : {', '.join(sorted(listened)) or '(nothing parsed)'}")
    if missing:
        print(f"MISSING: {', '.join(missing)} — a task routed there is never consumed")
        return 1
    for queue, why in sorted(DURING_MIGRATION.items()):
        if queue in needed and queue not in listened:
            print(f"pending: {queue} is routed but not consumed yet — {why}")
    if extra:
        print(f"note: the worker also listens on {', '.join(extra)} (harmless)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
