"""The highest record id a sweep may hand out, discovered rather than guessed.

MAL and Bangumi both issue record ids from a monotonically increasing space and
both keep their newest entries at the top of it, so the sweep that enumerates
the catalogue needs one number: how far up the space currently goes. Both used a
constant for that bound - ``MAL_MAX_ANIME_ID`` - which is a number somebody has
to remember to raise, and a sweep that stops short of the newest ids quietly
stops syncing them.

The bound is discoverable instead: walk upward from the last id we know exists
until enough ids in a row answer "no such record". A run that stops early (a
provider outage, a rate limit) keeps whatever it already proved, so the frontier
only ever moves on evidence.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from django.db.models import IntegerField, Max
from django.db.models.functions import Cast

from apps.index.models import ProviderRecord
from apps.sync.models import SyncState
from apps.sync.providers.exceptions import ProviderAPIError

FRONTIER_TASK_NAME = "provider_frontier"
# External ids are text upstream (VNDB uses ``v1234``), so a stored maximum is
# only meaningful for the numeric id spaces a sweep walks.
NUMERIC_ID = r"^[0-9]+$"


@dataclass(frozen=True, slots=True)
class Frontier:
    """Where an id space currently ends, and how far it has been probed."""

    highest_existing_id: int
    probed_to: int
    seed: int

    @property
    def ceiling(self) -> int:
        """Last id a sweep may hand out: it has never been contradicted."""
        return max(self.highest_existing_id, self.probed_to, self.seed)


def frontier_shard(*, provider_slug: str, namespace_slug: str) -> str:
    return f"{provider_slug}:{namespace_slug}"


def highest_stored_id(*, provider_slug: str, namespace_slug: str) -> int:
    """Highest id this catalogue already holds from a provider's id space.

    Used as the seed when a probe has no recorded frontier yet: starting the
    walk below the ids we already know about would record a frontier *behind*
    the data.
    """
    value = (
        ProviderRecord.objects.filter(
            namespace__provider__slug=provider_slug,
            namespace__slug=namespace_slug,
            external_id__regex=NUMERIC_ID,
        )
        .annotate(numeric_id=Cast("external_id", output_field=IntegerField()))
        .aggregate(highest=Max("numeric_id"))
        .get("highest")
    )
    return int(value or 0)


def read_frontier(*, provider_slug: str, namespace_slug: str, seed: int) -> Frontier:
    """The recorded frontier, or the configured seed before the first probe."""
    state = SyncState.objects.filter(
        task_name=FRONTIER_TASK_NAME,
        shard=frontier_shard(
            provider_slug=provider_slug, namespace_slug=namespace_slug
        ),
    ).first()
    if state is None:
        return Frontier(highest_existing_id=seed, probed_to=seed, seed=seed)
    return Frontier(
        highest_existing_id=state.end_id or seed,
        probed_to=max(state.current_id, state.end_id or 0, seed),
        seed=seed,
    )


def probe_frontier(
    *,
    provider_slug: str,
    namespace_slug: str,
    fetch: Callable[[int], Any],
    seed: int,
    window: int,
    max_misses: int,
) -> dict[str, Any]:
    """Walk ids upward until ``max_misses`` in a row do not exist.

    ``fetch`` answers with anything for an id that exists and raises a
    ``ProviderAPIError`` carrying ``is_not_found`` for one that does not. Any
    other failure ends the run without recording it as a miss: a provider that
    is rate limiting us must not look like a provider that ran out of records.
    """
    current = read_frontier(
        provider_slug=provider_slug, namespace_slug=namespace_slug, seed=seed
    )
    highest = current.highest_existing_id
    probed_to = current.ceiling
    misses = 0
    probed = 0
    stopped_by = "window"

    while probed < max(1, window) and misses < max(1, max_misses):
        candidate = probed_to + 1
        probed += 1
        try:
            fetch(candidate)
        except ProviderAPIError as exc:
            if not exc.is_not_found:
                stopped_by = "provider_error"
                break
            misses += 1
            probed_to = candidate
            continue
        except Exception:
            stopped_by = "unexpected_error"
            break
        highest = candidate
        probed_to = candidate
        misses = 0
    else:
        if misses >= max(1, max_misses):
            stopped_by = "missing_run"

    # An outage leaves the frontier exactly as it was; recording it again would
    # only dirty the table.
    if probed and (highest, probed_to) != (
        current.highest_existing_id,
        current.ceiling,
    ):
        SyncState.objects.update_or_create(
            task_name=FRONTIER_TASK_NAME,
            shard=frontier_shard(
                provider_slug=provider_slug, namespace_slug=namespace_slug
            ),
            defaults={
                "current_id": probed_to,
                "end_id": highest,
                "status": SyncState.Status.FINISHED,
            },
        )

    return {
        "provider": provider_slug,
        "namespace": namespace_slug,
        "highest_existing_id": highest,
        "probed_to": probed_to,
        "probed": probed,
        "misses": misses,
        "stopped_by": stopped_by,
    }
