from http.cookies import SimpleCookie
from types import SimpleNamespace

import httpx
import pytest
from fastapi import Response

from api.config import Settings, settings
from api.contexts.access.api import session as password_session
from api.contexts.access.cookies import clear_refresh_cookie, set_refresh_cookie
from api.db import get_session
from api.main import create_app


@pytest.mark.parametrize("prefix", ["REFRESH_COOKIE_", "JWT_REFRESH_COOKIE_"])
def test_cookie_environment_configuration(monkeypatch, prefix):
    values = {
        "NAME": "custom_refresh",
        "PATH": "/api/v1/auth/",
        "DOMAIN": ".example.com",
        "SECURE": "true",
        "SAMESITE": "Strict",
        "MAX_AGE": "3600",
    }
    for key, value in values.items():
        monkeypatch.setenv(prefix + key, value)
    configured = Settings(_env_file=None)
    assert configured.refresh_cookie_name == "custom_refresh"
    assert configured.refresh_cookie_path == "/api/v1/auth/"
    assert configured.refresh_cookie_domain == ".example.com"
    assert configured.refresh_cookie_secure is True
    assert configured.refresh_cookie_samesite == "strict"
    assert configured.refresh_cookie_max_age == 3600


def test_signing_key_environment_configuration(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "current-key")
    assert Settings(_env_file=None).jwt_secret == "current-key"


def test_empty_domain_is_host_only():
    assert Settings(_env_file=None, refresh_cookie_domain="").refresh_cookie_domain is None


def test_cookie_issue_and_clear_share_the_configured_scope(monkeypatch):
    monkeypatch.setattr(settings, "refresh_cookie_name", "custom_refresh")
    monkeypatch.setattr(settings, "refresh_cookie_domain", ".example.com")
    monkeypatch.setattr(settings, "refresh_cookie_secure", True)
    monkeypatch.setattr(settings, "refresh_cookie_samesite", "strict")
    monkeypatch.setattr(settings, "refresh_cookie_max_age", 3600)
    issued = Response()
    set_refresh_cookie(issued, "refresh-value")
    cleared = Response()
    clear_refresh_cookie(cleared)
    issue_cookie = SimpleCookie(issued.headers["set-cookie"])["custom_refresh"]
    clear_cookie = SimpleCookie(cleared.headers["set-cookie"])["custom_refresh"]
    for attribute in ["domain", "path", "secure", "httponly", "samesite"]:
        assert issue_cookie[attribute] == clear_cookie[attribute]
    assert issue_cookie["domain"] == ".example.com"
    assert issue_cookie["max-age"] == "3600"
    assert clear_cookie["max-age"] == "0"


@pytest.mark.asyncio
async def test_login_and_logout_use_the_configured_cookie(monkeypatch):
    monkeypatch.setattr(settings, "refresh_cookie_domain", ".example.com")
    monkeypatch.setattr(settings, "refresh_cookie_secure", True)
    monkeypatch.setattr(settings, "refresh_cookie_max_age", 3600)

    async def user_lookup(session, email):
        return SimpleNamespace(id=7, email=email, password="stored-password", is_active=True)

    async def database():
        yield object()

    monkeypatch.setattr(password_session, "_user", user_lookup)
    monkeypatch.setattr(password_session, "verify_password", lambda *_: True)
    monkeypatch.setattr(password_session, "create_tokens", lambda **_: ("access", "refresh"))
    app = create_app()
    app.dependency_overrides[get_session] = database
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="https://example.com"
    ) as client:
        login = await client.post(
            "/api/v1/auth/sessions/password/",
            json={"email": "user@example.com", "password": "password"},
        )
        assert login.status_code == 200
        issued = SimpleCookie(login.headers["set-cookie"])[settings.refresh_cookie_name]
        assert issued["secure"] and issued["domain"] == ".example.com"
        assert issued["max-age"] == "3600"
        logout = await client.post("/api/v1/auth/session/")
        assert logout.status_code == 204
        cleared = SimpleCookie(logout.headers["set-cookie"])[settings.refresh_cookie_name]
        assert cleared["domain"] == issued["domain"] and cleared["max-age"] == "0"
