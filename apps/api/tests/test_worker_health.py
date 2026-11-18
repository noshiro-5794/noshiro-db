from unittest.mock import MagicMock

import pytest

from api.worker import health


def test_missing_redis_configuration_fails_health_check(monkeypatch):
    monkeypatch.delenv("REDIS_CACHE_URL", raising=False)
    monkeypatch.delenv("CELERY_BROKER_URL", raising=False)
    assert health.healthy() is False


@pytest.mark.parametrize("value,expected", [(b"heartbeat", True), (None, False)])
def test_beat_health_uses_the_expiring_published_heartbeat(monkeypatch, value, expected):
    monkeypatch.setenv("REDIS_CACHE_URL", "redis://test/1")
    client = MagicMock()
    client.__enter__.return_value.get.return_value = value
    factory = MagicMock(return_value=client)
    monkeypatch.setattr(health.Redis, "from_url", factory)
    assert health.healthy() is expected
    factory.assert_called_once_with("redis://test/1", socket_timeout=3, socket_connect_timeout=3)
