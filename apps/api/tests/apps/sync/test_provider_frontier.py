import pytest

from apps.index.models import Provider, ProviderNamespace, ProviderRecord
from apps.sync.models import SyncState
from apps.sync.providers.exceptions import ProviderAPIError
from apps.sync.providers.frontier import (
    Frontier,
    highest_stored_id,
    probe_frontier,
    read_frontier,
)

PROVIDER = "mal"
NAMESPACE = "anime"


def _record(external_id: str) -> ProviderRecord:
    provider, _ = Provider.objects.get_or_create(
        slug=PROVIDER, defaults={"name": "MAL", "base_url": "https://example.test"}
    )
    namespace, _ = ProviderNamespace.objects.get_or_create(
        provider=provider,
        slug=NAMESPACE,
        defaults={"resource_type": "subject"},
    )
    return ProviderRecord.objects.create(
        namespace=namespace,
        external_id=external_id,
        status=ProviderRecord.Status.ACTIVE,
    )


@pytest.mark.django_db
def test_a_probe_without_a_record_uses_the_seed() -> None:
    frontier = read_frontier(provider_slug=PROVIDER, namespace_slug=NAMESPACE, seed=70)

    assert frontier.ceiling == 70


@pytest.mark.django_db
def test_the_seed_never_sits_below_the_ids_already_stored() -> None:
    _record("501")
    _record("not-a-number")

    assert highest_stored_id(provider_slug=PROVIDER, namespace_slug=NAMESPACE) == 501


@pytest.mark.django_db
def test_a_probe_walks_up_until_records_stop_answering() -> None:
    existing = {501, 502, 505, 506}

    def fetch(candidate: int):
        if candidate in existing:
            return {"id": candidate}
        raise ProviderAPIError("gone", status_code=404)

    first = probe_frontier(
        provider_slug=PROVIDER,
        namespace_slug=NAMESPACE,
        fetch=fetch,
        seed=500,
        window=100,
        max_misses=2,
    )

    # Two missing ids in a row end the run: 503 and 504 are the gap.
    assert first["highest_existing_id"] == 502
    assert first["probed_to"] == 504
    assert first["stopped_by"] == "missing_run"

    # The ceiling keeps the ids that were probed and not contradicted, so the
    # next run starts above the gap and finds 505 and 506 rather than stopping
    # at it for good.
    second = probe_frontier(
        provider_slug=PROVIDER,
        namespace_slug=NAMESPACE,
        fetch=fetch,
        seed=500,
        window=100,
        max_misses=2,
    )

    assert second["highest_existing_id"] == 506
    recorded = read_frontier(provider_slug=PROVIDER, namespace_slug=NAMESPACE, seed=500)
    assert recorded.highest_existing_id == 506
    assert recorded.ceiling == 508


@pytest.mark.django_db
def test_a_provider_outage_ends_the_walk_without_recording_a_miss() -> None:
    def fetch(candidate: int):
        raise ProviderAPIError("rate limited", status_code=429)

    result = probe_frontier(
        provider_slug=PROVIDER,
        namespace_slug=NAMESPACE,
        fetch=fetch,
        seed=900,
        window=100,
        max_misses=2,
    )

    assert result["stopped_by"] == "provider_error"
    assert result["highest_existing_id"] == 900
    assert result["misses"] == 0
    assert not SyncState.objects.exists()


@pytest.mark.django_db
def test_the_window_bounds_one_run() -> None:
    def fetch(candidate: int):
        return {"id": candidate}

    result = probe_frontier(
        provider_slug=PROVIDER,
        namespace_slug=NAMESPACE,
        fetch=fetch,
        seed=10,
        window=5,
        max_misses=2,
    )

    assert result["probed"] == 5
    assert result["stopped_by"] == "window"
    assert result["highest_existing_id"] == 15


def test_ceiling_takes_the_highest_of_the_signals() -> None:
    assert Frontier(highest_existing_id=10, probed_to=40, seed=5).ceiling == 40
    assert Frontier(highest_existing_id=90, probed_to=40, seed=5).ceiling == 90
