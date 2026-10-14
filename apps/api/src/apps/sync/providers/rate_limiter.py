import threading
import time
from collections.abc import Mapping
from contextlib import suppress

from django.conf import settings
from django.core.cache import cache

GATE_KEY = "noshiro:provider-rate:{name}:next"
LOCK_KEY = "noshiro:provider-rate:{name}:lock"

# A provider either publishes its budget (AniList sends the three
# ``X-RateLimit-*`` headers) or it does not (MAL publishes none). The interval
# below is the floor for every provider; the headers only ever raise it, never
# lower it, so a missing or wrong header cannot make us faster than the floor.
#
# ``X-RateLimit-Reset`` is a *duration* in AniList's documentation and an
# absolute epoch in some other stacks' conventions, so both are accepted.
EPOCH_THRESHOLD = 1_000_000_000
MAX_GATE_SECONDS = 3600.0
MAX_SLEEP_SLICE = 5.0


def parse_gate_delay(headers: Mapping[str, str], *, now: float) -> float:
    """Seconds to hold off, derived from whatever budget headers are present."""
    retry_after = _parse_seconds(headers.get("Retry-After"))
    if retry_after is not None:
        return retry_after

    remaining = _parse_int(headers.get("X-RateLimit-Remaining"))
    if remaining is None:
        return 0.0
    # Spending the last request of a window is how a client discovers the limit
    # the hard way, so stop one short of it and wait for the reset.
    if remaining > 1:
        return 0.0
    reset = _parse_seconds(headers.get("X-RateLimit-Reset"))
    if reset is None:
        return 0.0
    return reset if reset < EPOCH_THRESHOLD else reset - now


def _parse_seconds(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _parse_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


class RateLimiter:
    """In-process interval limiter, used when the shared cache is unavailable."""

    def __init__(self, interval: float) -> None:
        self.interval = max(0.0, interval)
        self.lock = threading.Lock()
        self.last_time = 0.0
        self.gate = 0.0

    def acquire(self) -> None:
        with self.lock:
            now = time.monotonic()
            target = max(self.last_time + self.interval, self.gate)
            remaining = target - now
            if remaining > 0:
                time.sleep(remaining)
            self.last_time = time.monotonic()

    def observe(self, headers: Mapping[str, str]) -> None:
        self._hold(parse_gate_delay(headers, now=time.time()))

    def penalize(self, seconds: float) -> None:
        self._hold(seconds)

    def _hold(self, seconds: float) -> None:
        if seconds <= 0:
            return
        with self.lock:
            self.gate = max(self.gate, time.monotonic() + seconds)


class DistributedRateLimiter:
    """A shared interval floor that a provider's own budget headers can raise.

    The floor keeps us inside a documented requests-per-second limit; the
    headers keep us inside a budget we would otherwise have to guess at. AniList
    answers unauthenticated calls with ``X-RateLimit-Limit: 30`` per minute —
    three times slower than the interval this repository used to carry — and
    exposes the budget precisely so clients pace themselves with it instead of
    discovering it through 429s.

    One shared "do not send before" timestamp carries both signals, so a 429
    seen by one worker holds every worker back. The wait happens outside the
    claim lock: a worker that is sleeping must not keep the others from
    claiming the slot it is waiting for.
    """

    def __init__(
        self,
        name: str,
        interval: float,
        *,
        lock_ttl: int = 10,
        allow_fallback: bool | None = None,
    ) -> None:
        self.name = name
        self.interval = max(0.0, interval)
        self.lock_ttl = max(2, lock_ttl)
        self._fallback = RateLimiter(interval)
        self.allow_fallback = (
            settings.DEBUG if allow_fallback is None else allow_fallback
        )

    def acquire(self) -> None:
        if self.interval <= 0:
            return
        while True:
            wait = self._gate_wait()
            if wait > 0:
                time.sleep(min(wait, MAX_SLEEP_SLICE))
                continue
            # A slot is only ours once the claim succeeds; when another worker
            # raised the gate first, wait it out and try again.
            if self._claim():
                return

    def observe(self, headers: Mapping[str, str]) -> None:
        """Fold a provider's budget headers into the shared gate."""
        self._fallback.observe(headers)
        self._hold(parse_gate_delay(headers, now=time.time()))

    def penalize(self, seconds: float) -> None:
        """Hold every worker back, e.g. after a 429 or a 5xx."""
        self._fallback.penalize(seconds)
        self._hold(seconds)

    def _hold(self, seconds: float) -> None:
        if seconds <= 0:
            return
        seconds = min(seconds, MAX_GATE_SECONDS)
        key = GATE_KEY.format(name=self.name)
        try:
            current = float(cache.get(key) or 0.0)
            target = time.time() + seconds
            if target > current:
                cache.set(key, target, timeout=max(60, int(seconds) + 60))
        except Exception:
            # The request this observation describes has already been sent, so
            # failing here would only invent an error. ``acquire`` still fails
            # fast when the shared cache is gone, which is what keeps a lost
            # observation from turning into a burst.
            return

    def _gate_wait(self) -> float:
        key = GATE_KEY.format(name=self.name)
        try:
            target = float(cache.get(key) or 0.0)
        except Exception:
            if self.allow_fallback:
                return max(0.0, self._fallback.gate - time.monotonic())
            raise
        return max(0.0, target - time.time())

    def _claim(self) -> bool:
        """Take the next slot, spacing claims by the configured interval."""
        lock_key = LOCK_KEY.format(name=self.name)
        gate_key = GATE_KEY.format(name=self.name)
        while True:
            try:
                acquired = cache.add(lock_key, "1", timeout=self.lock_ttl)
            except Exception:
                # Local development/tests may not have Redis. Production fails
                # fast instead of bursting past the provider's rate limit; the
                # campaign retry/backoff machinery then retries the step.
                if self.allow_fallback:
                    self._fallback.acquire()
                    return True
                raise
            if not acquired:
                time.sleep(0.02)
                continue
            try:
                now = time.time()
                next_at = float(cache.get(gate_key) or 0.0)
                if next_at > now:
                    # Another worker raised the gate between our check and our
                    # claim: wait it out rather than claiming a slot under it.
                    return False
                cache.set(
                    gate_key,
                    now + self.interval,
                    timeout=max(60, int(self.interval * 10)),
                )
                return True
            finally:
                with suppress(Exception):
                    cache.delete(lock_key)
