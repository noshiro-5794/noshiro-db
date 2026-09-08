from unittest.mock import Mock

from apps.ai.tools.bangumi import (
    BangumiSearchInput,
    BangumiSearchTool,
)
from apps.ai.tools.registry import create_default_tool_registry
from apps.sync.providers.bangumi import BangumiAPIError


def test_default_registry_registers_bangumi_search_tool() -> None:
    registry = create_default_tool_registry()

    tool = registry.get("bangumi.search_subjects")

    assert tool.permission == "bangumi:search"
    assert tool.records_evidence is True
    assert tool.risk_level == "read_only"


def test_bangumi_search_tool_returns_compact_results() -> None:
    client = Mock()
    client.search_subjects.return_value = {
        "data": [
            {
                "id": 23456,
                "name": "Test Anime",
                "name_cn": "测试动画",
                "date": "2026-04-01",
                "summary": "Summary",
                "platform": "TV",
                "images": {"large": "https://lain.bgm.tv/pic/cover/large/x.jpg"},
            }
        ],
        "total": 1,
    }

    result = BangumiSearchTool(client).execute(
        BangumiSearchInput(keyword="Test Anime", limit=5)
    )

    assert result.available is True
    assert result.total == 1
    assert result.results == [
        {
            "id": 23456,
            "name": "Test Anime",
            "name_cn": "测试动画",
            "date": "2026-04-01",
            "summary": "Summary",
            "platform": "TV",
            "images": {"large": "https://lain.bgm.tv/pic/cover/large/x.jpg"},
            "url": "https://bgm.tv/subject/23456",
        }
    ]
    client.search_subjects.assert_called_once_with(
        keyword="Test Anime",
        subject_types=(2,),
        limit=5,
        offset=0,
    )


def test_bangumi_search_tool_reports_unavailable_instead_of_raising() -> None:
    client = Mock()
    client.search_subjects.side_effect = BangumiAPIError(
        "Bangumi API returned 502: upstream",
        status_code=502,
    )

    result = BangumiSearchTool(client).execute(BangumiSearchInput(keyword="Test Anime"))

    assert result.available is False
    assert "502" in result.reason
    assert result.results == []
