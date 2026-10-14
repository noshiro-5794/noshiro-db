from unittest.mock import Mock

import pytest

from apps.index.models import Provider, ProviderNamespace, ProviderRecord
from apps.sync.models import SyncState
from apps.sync.providers.anilist import AniListClient
from apps.sync.providers.bangumi import (
    BANGUMI_SOURCE,
    BANGUMI_SUBJECT_NAMESPACE,
    BangumiClient,
)
from apps.sync.providers.exceptions import (
    AniListAPIError,
    VNDBAPIError,
)
from apps.sync.providers.vndb import VNDB_SOURCE, VNDB_VN_NAMESPACE, VNDBClient
from apps.sync.services.campaign import (
    PROVIDERS,
    SyncCampaignService,
)
from apps.sync.services.relation_types import canonical_relation_type


def test_provider_http_errors_expose_retry_policy() -> None:
    rate_limited = VNDBAPIError("busy", status_code=429, retry_after=4)
    permanent = AniListAPIError("invalid", status_code=400)

    assert rate_limited.retryable is True
    assert rate_limited.retry_after == 4
    assert rate_limited.error_code == "http_429"
    assert permanent.retryable is False


def test_relation_vocabularies_share_canonical_slugs() -> None:
    assert canonical_relation_type("vndb", "seq") == "sequel"
    assert canonical_relation_type("anilist", "SEQUEL") == "sequel"
    assert canonical_relation_type("bangumi", "续作") == "sequel"


def test_unknown_relation_keeps_a_stable_slug() -> None:
    assert canonical_relation_type("custom", "Official Remake") == "official-remake"


@pytest.mark.django_db
def test_bangumi_catalog_discovery_walks_the_id_space() -> None:
    """The browse view is bounded and approximate; the id space is neither."""
    SyncState.objects.create(
        task_name="provider_frontier",
        shard="bangumi:subject",
        current_id=204,
        end_id=200,
        status=SyncState.Status.FINISHED,
    )
    http_client = Mock()
    client = BangumiClient(http_client)

    first = client.discover_subject_page(cursor=None, page_size=3)
    assert first.external_ids == ("1", "2", "3")
    assert first.next_cursor == "4"
    assert first.total_count == 204

    last = client.discover_subject_page(cursor="202", page_size=3)
    assert last.external_ids == ("202", "203", "204")
    assert last.next_cursor is None

    exhausted = client.discover_subject_page(cursor="205", page_size=3)
    assert exhausted.external_ids == ()
    assert exhausted.next_cursor is None
    # The sweep never asks the browse endpoint, and never fetches a payload to
    # hand out an id: the importer does that, one id at a time.
    http_client.get.assert_not_called()
    http_client.post.assert_not_called()


@pytest.mark.django_db
def test_bangumi_delta_refetches_known_active_records() -> None:
    provider = Provider.objects.create(slug=BANGUMI_SOURCE.slug, name="Bangumi")
    namespace = ProviderNamespace.objects.create(
        provider=provider, slug=BANGUMI_SUBJECT_NAMESPACE.slug, resource_type="subject"
    )
    ProviderRecord.objects.create(
        namespace=namespace, external_id="1", origin="api", status="active"
    )
    ProviderRecord.objects.create(
        namespace=namespace, external_id="2", origin="api", status="active"
    )
    client = BangumiClient(Mock())

    page = client.discover_subject_delta_page(watermark="0", cursor="0", page_size=1)

    assert page.external_ids == ("1",)
    assert page.next_cursor == "1"
    assert page.total_count == 2


@pytest.mark.django_db
def test_vndb_delta_refetches_known_active_records() -> None:
    provider = Provider.objects.create(slug=VNDB_SOURCE.slug, name="VNDB")
    namespace = ProviderNamespace.objects.create(
        provider=provider, slug=VNDB_VN_NAMESPACE.slug, resource_type="subject"
    )
    ProviderRecord.objects.create(
        namespace=namespace, external_id="v1", origin="api", status="active"
    )
    client = VNDBClient(Mock())

    client.query = Mock(
        return_value={
            "results": [{"id": "v2"}, {"id": "v3"}],
            "more": True,
            "count": 9,
        }
    )

    page = client.discover_vn_delta_page(watermark="0", cursor=None, page_size=10)

    # With no watermark yet the walk starts above the highest id we hold, so a
    # first run looks at new works rather than re-walking the whole space.
    assert client.query.call_args.kwargs["filters"] == ["id", ">", "v1"]
    assert client.query.call_args.kwargs["sort"] == "id"
    assert page.external_ids == ("v2", "v3")
    assert page.next_cursor == "2"
    assert page.watermark == "3"
    assert page.total_count == 9


@pytest.mark.django_db
def test_vndb_delta_continues_above_the_watermark() -> None:
    client = VNDBClient(Mock())
    client.query = Mock(return_value={"results": [], "more": False, "count": 0})

    page = client.discover_vn_delta_page(watermark="60003", cursor="4", page_size=10)

    assert client.query.call_args.kwargs["filters"] == ["id", ">", "v60003"]
    assert client.query.call_args.kwargs["page"] == 4
    assert page.external_ids == ()
    assert page.next_cursor is None
    assert page.watermark == "60003"


def test_campaign_provider_registry_wires_delta_and_discovery_contract() -> None:
    assert PROVIDERS["vndb"].discover_delta is not None
    assert PROVIDERS["anilist"].discover_delta is not None
    assert PROVIDERS["bangumi"].discover_delta is not None
    assert PROVIDERS["vndb"].discovery_complete is True
    assert PROVIDERS["anilist"].discovery_complete is True
    assert PROVIDERS["bangumi"].discovery_complete is False


def test_anilist_delta_watermark_advances_to_max_air_date() -> None:
    client = AniListClient(Mock())
    client._post = Mock(
        return_value={
            "Page": {
                "pageInfo": {"hasNextPage": True},
                "media": [
                    {"id": 1, "startDate": {"year": 2025, "month": 12, "day": 30}},
                    {"id": 2, "startDate": {"year": 2026, "month": 1, "day": 3}},
                ],
            }
        }
    )

    page = client.discover_anime_delta_page(
        watermark="20250101", cursor="1", page_size=50
    )

    assert page.external_ids == ("1", "2")
    assert page.next_cursor == "2"
    assert page.watermark == "20260102"
    assert client._post.call_args.args[1] == {
        "page": 1,
        "perPage": 50,
        "startedAfter": 20250101,
    }


def test_accumulate_watermark_merges_numeric_deltas() -> None:
    class FakePage:
        watermark: str

        def __init__(self, watermark):
            self.watermark = watermark

    assert SyncCampaignService._accumulate_watermark(None, FakePage("120")) == "120"
    assert SyncCampaignService._accumulate_watermark("100", FakePage("90")) == "100"
    assert SyncCampaignService._accumulate_watermark("100", FakePage("150")) == "150"
    assert (
        SyncCampaignService._accumulate_watermark(
            "100", FakePage("known-record-reconciliation")
        )
        == "100"
    )


def test_missing_reconciliation_requires_provable_complete_discovery() -> None:
    class FakeCampaign:
        def __init__(self, provider_slug, campaign_type="full", parameters=None):
            self.provider_slug = provider_slug
            self.campaign_type = campaign_type
            self.parameters = parameters or {}

    assert (
        SyncCampaignService._can_mark_missing(
            FakeCampaign("vndb", parameters={"discovery": {"next_cursor": None}})
        )
        is True
    )
    assert (
        SyncCampaignService._can_mark_missing(
            FakeCampaign("anilist", parameters={"discovery": {"truncated": True}})
        )
        is False
    )
    assert (
        SyncCampaignService._can_mark_missing(
            FakeCampaign("bangumi", parameters={"discovery": {"next_cursor": None}})
        )
        is False
    )
    assert (
        SyncCampaignService._can_mark_missing(
            FakeCampaign(
                "bangumi",
                parameters={
                    "discovery": {"next_cursor": None},
                    "reconcile_missing": True,
                },
            )
        )
        is True
    )
    assert (
        SyncCampaignService._can_mark_missing(FakeCampaign("anilist", "incremental"))
        is False
    )


def test_incremental_watermark_promoted_only_at_review() -> None:
    class FakeCampaign:
        campaign_type = "incremental"
        parameters = {"pending_watermark": "1700000000"}
        save_calls: list[tuple] = []

        def save(self, **kwargs) -> None:
            self.save_calls.append(kwargs)

    campaign = FakeCampaign()

    SyncCampaignService._promote_watermark(campaign)

    assert campaign.parameters == {"watermark": "1700000000"}
    assert campaign.save_calls == [{"update_fields": ["parameters", "updated_at"]}]


def test_full_campaign_never_promotes_watermark() -> None:
    class FakeCampaign:
        campaign_type = "full"
        parameters = {"pending_watermark": "1700000000"}
        save_calls: list[tuple] = []

        def save(self, **kwargs) -> None:
            self.save_calls.append(kwargs)

    campaign = FakeCampaign()

    SyncCampaignService._promote_watermark(campaign)

    assert campaign.parameters == {"pending_watermark": "1700000000"}
    assert campaign.save_calls == []


def test_truncated_incremental_never_promotes_watermark() -> None:
    class FakeCampaign:
        campaign_type = "incremental"
        parameters = {
            "discovery": {"truncated": True},
            "pending_watermark": "1700000000",
        }
        save_calls: list[tuple] = []

        def save(self, **kwargs) -> None:
            self.save_calls.append(kwargs)

    campaign = FakeCampaign()

    SyncCampaignService._promote_watermark(campaign)

    assert campaign.parameters == {
        "discovery": {"truncated": True},
        "pending_watermark": "1700000000",
    }
    assert campaign.save_calls == []


@pytest.mark.django_db
def test_review_marks_agent_run_complete() -> None:
    from apps.ai.models import AgentRun

    run = AgentRun.objects.create(
        kind=AgentRun.Kind.ADMIN_SYNC,
        title="campaign",
        idempotency_key="k",
        idempotency_scope="sync:test",
    )

    class FakeCampaign:
        agent_run_id = run.pk

    SyncCampaignService._mark_agent_run_complete(FakeCampaign())

    run.refresh_from_db()
    assert run.status == AgentRun.Status.SUCCEEDED
    assert run.finished_at is not None
