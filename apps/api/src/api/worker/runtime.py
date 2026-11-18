"""Running one coroutine inside a synchronous Celery task."""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import Any


def run(work: Coroutine[Any, Any, Any]) -> Any:
    return asyncio.run(work)
