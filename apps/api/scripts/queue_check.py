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
APP = REPO / "apps/api/src/api/worker/app.py"
COMPOSE = REPO / "deploy/compose.prod.yml"

ROUTE = re.compile(r'"apps\.[\w.*]+"\s*:\s*\{\s*"queue"\s*:\s*"([\w.-]+)"')
DEFAULT_QUEUE = re.compile(r'task_default_queue\s*=\s*"([\w.-]+)"')
LISTEN = re.compile(r"-Q\s+([\w,.-]+)")


def routed_queues() -> tuple[set[str], str]:
    text = APP.read_text()
    routed = set(ROUTE.findall(text))
    default = DEFAULT_QUEUE.search(text)
    return routed, (default.group(1) if default else "realtime")


def listened_queues() -> set[str]:
    queues: set[str] = set()
    for match in LISTEN.findall(COMPOSE.read_text()):
        queues.update(queue.strip() for queue in match.split(",") if queue.strip())
    return queues


def main() -> int:
    routed, default = routed_queues()
    listened = listened_queues()
    needed = routed | {default}
    missing = sorted(needed - listened)
    extra = sorted(listened - needed)
    print(f"routing writes to : {', '.join(sorted(needed))}")
    print(f"worker listens on : {', '.join(sorted(listened)) or '(nothing parsed)'}")
    if missing:
        print(f"MISSING: {', '.join(missing)} — a task routed there is never consumed")
        return 1
    if extra:
        print(f"note: the worker also listens on {', '.join(extra)} (harmless)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
