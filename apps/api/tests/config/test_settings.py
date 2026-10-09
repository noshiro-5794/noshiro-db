import pytest
from django.conf import settings

from config.settings.base import _normalize_minio_endpoint, _outbound_user_agent


class TestOutboundIdentity:
    def test_provider_user_agents_default_to_the_shared_outbound_identity(
        self,
    ) -> None:
        """A provider User-Agent should only ever come from one place.

        A per-provider override is legitimate, but it has to be an explicit
        environment choice rather than a second default in the source tree.
        """
        for name in (
            "BANGUMI_USER_AGENT",
            "VNDB_USER_AGENT",
            "ANILIST_USER_AGENT",
            "MAL_USER_AGENT",
        ):
            assert getattr(settings, name) == settings.OUTBOUND_USER_AGENT

    def test_outbound_user_agent_combines_name_and_contact(self) -> None:
        assert (
            _outbound_user_agent("acme-db", "ops@example.com")
            == "acme-db (+ops@example.com)"
        )

    def test_outbound_user_agent_degrades_to_the_bare_name_without_contact(
        self,
    ) -> None:
        assert _outbound_user_agent("acme-db", "") == "acme-db"


class TestNormalizeMinioEndpoint:
    def test_returns_none_for_none(self) -> None:
        assert _normalize_minio_endpoint(None) == (None, None)

    def test_returns_none_for_empty(self) -> None:
        assert _normalize_minio_endpoint("") == (None, None)

    def test_parses_https_url(self) -> None:
        netloc, uses_https = _normalize_minio_endpoint("https://minio.example.com")
        assert netloc == "minio.example.com"
        assert uses_https is True

    def test_parses_http_url(self) -> None:
        netloc, uses_https = _normalize_minio_endpoint("http://minio.example.com")
        assert netloc == "minio.example.com"
        assert uses_https is False

    def test_returns_raw_endpoint_for_no_scheme(self) -> None:
        endpoint, uses_https = _normalize_minio_endpoint("minio:9000")
        assert endpoint == "minio:9000"
        assert uses_https is None


def test_every_scheduled_task_is_registered_with_celery() -> None:
    """A beat entry that names an unregistered task fails silently at 5am.

    Celery binds ``@shared_task`` to the defining module, so a schedule has to
    carry the full module path. A short path looked fine in review while the
    worker answered "Received unregistered task" and the ranking went stale for
    a week.
    """
    from config.celery import app

    app.loader.import_default_modules()
    registered = set(app.tasks)
    scheduled = {
        key: entry["task"] for key, entry in settings.CELERY_BEAT_SCHEDULE.items()
    }

    missing = {key: name for key, name in scheduled.items() if name not in registered}

    assert missing == {}


def test_scheduled_task_names_point_at_their_defining_module() -> None:
    """Guards against a schedule that only matches because of an alias."""
    scheduled = {entry["task"] for entry in settings.CELERY_BEAT_SCHEDULE.values()}

    assert all("." in name and not name.endswith("._task") for name in scheduled)
    assert "apps.index.tasks.popularity.refresh_popularity_task" in scheduled


def test_redis_cache_gets_a_socket_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    """A stalled Redis socket must raise, not park the worker forever.

    redis-py defaults to no timeout, so one half-open connection hangs a task
    (and the rate limiter it holds) until the soft time limit kills it.
    """
    import importlib

    import config.settings.base as base

    # The cache options are built while the settings module is imported, so the
    # URL has to reach the process environment - override_settings is read too
    # late and the module would keep the locmem cache.
    monkeypatch.setenv("CACHE_URL", "redis://cache:6379/1")
    try:
        reloaded = importlib.reload(base)
        options = reloaded.CACHES["default"].get("OPTIONS", {})
    finally:
        monkeypatch.delenv("CACHE_URL", raising=False)
        importlib.reload(base)

    assert options.get("socket_timeout", 0) > 0
    assert options.get("socket_connect_timeout", 0) > 0
