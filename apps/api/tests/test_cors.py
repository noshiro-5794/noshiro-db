import httpx
import pytest

from api.config import Settings, settings
from api.main import create_app


@pytest.mark.parametrize(
    "origins",
    [
        "https://noshiro.moe, https://www.noshiro.moe,",
        '["https://noshiro.moe", "https://www.noshiro.moe"]',
    ],
)
def test_cors_origins_accept_existing_and_json_environment_formats(monkeypatch, origins):
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", origins)
    assert Settings(_env_file=None).cors_allowed_origins == [
        "https://noshiro.moe",
        "https://www.noshiro.moe",
    ]


@pytest.mark.asyncio
async def test_browser_credentials_and_authorization_preflight(monkeypatch):
    monkeypatch.setattr(settings, "cors_allowed_origins", ["https://noshiro.moe"])
    monkeypatch.setattr(settings, "cors_allow_credentials", True)
    monkeypatch.setattr(settings, "cors_allow_all_origins", False)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app()), base_url="https://api.noshiro.moe"
    ) as client:
        preflight = await client.options(
            "/api/v1/auth/sessions/password/",
            headers={
                "Origin": "https://noshiro.moe",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )
        assert preflight.status_code == 200
        assert preflight.headers["access-control-allow-origin"] == "https://noshiro.moe"
        assert preflight.headers["access-control-allow-credentials"] == "true"
        error = await client.get("/missing/", headers={"Origin": "https://noshiro.moe"})
        assert error.status_code == 404
        assert error.headers["access-control-allow-origin"] == "https://noshiro.moe"
        refused = await client.options(
            "/api/v1/auth/sessions/password/",
            headers={
                "Origin": "https://unconfigured.example",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert refused.status_code == 400
        assert "access-control-allow-origin" not in refused.headers


@pytest.mark.asyncio
async def test_allow_all_origins_configuration(monkeypatch):
    monkeypatch.setattr(settings, "cors_allow_all_origins", True)
    monkeypatch.setattr(settings, "cors_allow_credentials", False)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app()), base_url="http://testserver"
    ) as client:
        response = await client.get("/health/live/", headers={"Origin": "https://example.com"})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "*"
