from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from starlette.requests import Request

from api.contexts.community.api import notifications
from api.shared.problems import ProblemError


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "value,expected",
    [
        (None, False),
        ("", None),
        ("true", True),
        ("1", True),
        ("YES", True),
        ("false", False),
        ("0", False),
        ("off", False),
    ],
)
async def test_notification_filter_preserves_query_boolean_spellings(monkeypatch, value, expected):
    listed = AsyncMock(return_value=([], None))
    monkeypatch.setattr(notifications, "list_for_user", listed)
    await notifications.notification_list(
        object(),
        Request({"type": "http", "method": "GET", "path": "/", "headers": []}),
        SimpleNamespace(id=1),
        is_read=value,
    )
    assert listed.call_args.kwargs["is_read"] is expected


@pytest.mark.asyncio
async def test_invalid_notification_filter_returns_existing_validation_envelope(monkeypatch):
    listed = AsyncMock()
    monkeypatch.setattr(notifications, "list_for_user", listed)
    with pytest.raises(ProblemError) as caught:
        await notifications.notification_list(
            object(),
            Request({"type": "http", "method": "GET", "path": "/", "headers": []}),
            SimpleNamespace(id=1),
            is_read="invalid",
        )
    assert caught.value.status_code == 400
    assert caught.value.errors == {"is_read": ["Must be a valid boolean."]}
    listed.assert_not_awaited()
