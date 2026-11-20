"""Verify that scheduled beat work has published its expiring heartbeat."""

import os
import sys

from redis import Redis


def healthy() -> bool:
    url = os.environ.get("REDIS_CACHE_URL") or os.environ.get("CELERY_BROKER_URL")
    if not url:
        return False
    with Redis.from_url(url, socket_timeout=3, socket_connect_timeout=3) as client:
        return bool(client.get("noshiro:beat:heartbeat"))


if __name__ == "__main__":
    sys.exit(0 if healthy() else 1)
