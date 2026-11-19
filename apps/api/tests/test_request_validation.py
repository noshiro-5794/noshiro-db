import json
from types import SimpleNamespace

import httpx
import pytest

from api.contexts.access.dependencies import current_user
from api.db import get_session
from api.main import create_app


@pytest.fixture
async def client():
    app = create_app()

    async def database():
        yield object()

    app.dependency_overrides[get_session] = database
    app.dependency_overrides[current_user] = lambda: SimpleNamespace(id=7)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        yield client


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path,field,message",
    [
        ("/api/v1/index/entities/?nsfw=invalid", "nsfw", "Must be a valid boolean."),
        (
            "/api/v1/users/me/library/entries/?tag_id=invalid",
            "tag_id",
            "A valid integer is required.",
        ),
    ],
)
async def test_query_validation_returns_legacy_problem_fields(client, path, field, message):
    response = await client.get(path)
    assert response.status_code == 400, response.text
    assert response.headers["content-type"] == "application/problem+json"
    body = response.json()
    assert body["detail"] == "Request validation failed."
    assert body["errors"] == {field: [message]}
    assert body["trace_id"] and body["instance"] == path


@pytest.mark.asyncio
async def test_missing_login_fields_use_existing_required_field_messages(client):
    response = await client.post("/api/v1/auth/sessions/password/", json={})
    assert response.status_code == 400
    assert response.json()["errors"] == {
        "email": ["This field is required."],
        "password": ["This field is required."],
    }


@pytest.mark.asyncio
async def test_invalid_path_identifier_is_a_404_problem(client):
    response = await client.get("/api/v1/users/me/library/entries/invalid/")
    assert response.status_code == 404 and response.json()["detail"] == "Not found."


@pytest.mark.asyncio
async def test_missing_routes_and_unsupported_methods_keep_problem_envelopes(client):
    missing = await client.get("/api/v1/missing/")
    assert missing.status_code == 404 and missing.json()["type"] == "about:blank"
    method = await client.get("/api/v1/auth/sessions/password/")
    assert method.status_code == 405 and method.json()["detail"] == 'Method "GET" not allowed.'
    assert method.headers["allow"] == "POST"


@pytest.mark.asyncio
async def test_malformed_json_preserves_parser_error_detail(client):
    response = await client.post(
        "/api/v1/auth/sessions/password/", content="{", headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 400
    try:
        json.loads("{")
    except ValueError as error:
        expected = f"JSON parse error - {error}"
    assert response.json()["detail"] == expected and "errors" not in response.json()


def test_openapi_documents_the_validation_problem_response():
    schema = create_app().openapi()
    responses = schema["paths"]["/api/v1/auth/sessions/password/"]["post"]["responses"]
    assert "422" not in responses
    assert responses["400"]["content"]["application/problem+json"]["schema"] == {
        "$ref": "#/components/schemas/ProblemDocument"
    }


@pytest.mark.asyncio
async def test_versioned_openapi_url_preserves_the_public_schema_endpoint(client):
    response = await client.get("/api/v1/openapi/")
    assert response.status_code == 200
    assert "/api/v1/auth/sessions/refresh/" in response.json()["paths"]
