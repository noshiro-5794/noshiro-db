from unittest.mock import patch

import pytest

from apps.sync.services.campaign_service import (
    CampaignProviderNotFound,
    SyncCampaignService,
    campaign_idempotency_key,
)


def test_campaign_idempotency_key_is_stable_for_mapping_equivalent_parameters() -> None:
    first = campaign_idempotency_key(
        provider_slug="vndb",
        campaign_type="full",
        parameters={"page_size": 100, "ai_sample_size": 16},
    )
    second = campaign_idempotency_key(
        provider_slug="vndb",
        campaign_type="full",
        parameters={"ai_sample_size": 16, "page_size": 100},
    )

    assert first == second
    assert first.startswith("vndb:full:")


def test_campaign_service_rejects_unregistered_provider() -> None:
    with pytest.raises(CampaignProviderNotFound, match="Unsupported campaign provider"):
        SyncCampaignService().provider_for("unknown")


def test_campaign_service_taxonomy_values_are_unique_and_bounded() -> None:
    values = SyncCampaignService._taxonomy_values(
        {
            "genres": ["Action", "Action", ""],
            "tags": [{"name": "Drama"}, "Drama", {"name": None}],
        }
    )

    assert values == ("Action", "Drama")


class TestDeltaWindow:
    """AniList caps page depth at 5000 entries, so a delta crawl must window."""

    def test_promotes_the_watermark_once_the_window_is_deep_enough(self) -> None:
        params = {"watermark": "100"}
        discovery = {"next_cursor": "81"}

        SyncCampaignService._promote_delta_window(
            params=params,
            discovery=discovery,
            pending="500",
            total_pages=80,
        )

        assert params["watermark"] == "500"
        assert "pending_watermark" not in params
        assert discovery["next_cursor"] == "1"

    def test_keeps_paging_inside_an_unfinished_window(self) -> None:
        params = {"watermark": "100"}
        discovery = {"next_cursor": "42"}

        SyncCampaignService._promote_delta_window(
            params=params,
            discovery=discovery,
            pending="500",
            total_pages=41,
        )

        assert params["watermark"] == "100"
        assert discovery["next_cursor"] == "42"

    def test_does_not_loop_when_no_page_advanced_the_watermark(self) -> None:
        params = {"watermark": "500"}
        discovery = {"next_cursor": "80"}

        SyncCampaignService._promote_delta_window(
            params=params,
            discovery=discovery,
            pending="500",
            total_pages=80,
        )

        assert params["watermark"] == "500"
        assert discovery["next_cursor"] == "80"

    def test_ignores_a_finished_crawl(self) -> None:
        params = {"watermark": "100"}
        discovery = {"next_cursor": None}

        SyncCampaignService._promote_delta_window(
            params=params,
            discovery=discovery,
            pending="500",
            total_pages=80,
        )

        assert params["watermark"] == "100"


class _FakeCampaign:
    """Campaign stand-in whose persisted status only moves when a step runs."""

    def __init__(self, status: str) -> None:
        self.status = status
        self.processed_items = 0
        self.total_items = 0
        self.refreshed = 0

    def refresh_from_db(self) -> None:
        self.refreshed += 1


class _StubCampaignService(SyncCampaignService):
    """Real watch loop, stubbed stepping."""

    def __init__(self, campaign: _FakeCampaign, step_statuses: list[str]) -> None:
        self.campaign = campaign
        self.step_statuses = list(step_statuses)
        self.runs = 0
        self.resumes = 0

    def run(self, campaign, *, max_items=None):
        self.runs += 1
        if self.step_statuses:
            self.campaign.status = self.step_statuses.pop(0)
        return self.campaign

    def resume(self, campaign):
        self.resumes += 1
        return self.campaign


def test_watch_steps_and_reports_until_the_campaign_is_terminal() -> None:
    campaign = _FakeCampaign("fetching")
    service = _StubCampaignService(campaign, ["fetching", "completed"])
    seen: list[str] = []

    with patch("apps.sync.services.campaign_service.time.sleep"):
        result = service.watch(
            campaign, delay=0, on_step=lambda stepped: seen.append(stepped.status)
        )

    assert result is campaign
    assert seen == ["fetching", "completed"]
    assert campaign.refreshed >= 2


def test_watch_resumes_a_failed_campaign() -> None:
    campaign = _FakeCampaign("failed")
    service = _StubCampaignService(campaign, ["completed"])

    with patch("apps.sync.services.campaign_service.time.sleep"):
        result = service.watch(campaign, delay=0)

    assert result is campaign
    assert service.resumes == 1
    assert service.runs == 1
