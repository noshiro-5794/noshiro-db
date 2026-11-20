from io import BytesIO
from unittest.mock import Mock
from uuid import UUID

import pytest
from botocore.stub import Stubber
from PIL import Image

from api.config import Settings, settings
from api.contexts.access import avatars
from api.contexts.access.api.avatars import avatar_storage
from api.contexts.access.profiles import get_or_create_profile
from api.contexts.presentation.fragments import fetch
from api.integrations.storage import ObjectStorage, StorageSettings
from tests.test_library_resources_transactions import library_client as library_client

PATH = "/api/v1/users/me/avatar/"


def image_bytes(format_name="PNG"):
    stream = BytesIO()
    Image.new("RGB", (2, 2), "blue").save(stream, format=format_name)
    return stream.getvalue()


@pytest.fixture
async def avatar_client(library_client, monkeypatch):
    session, client, data = library_client
    storage = ObjectStorage(
        StorageSettings(
            _env_file=None,
            S3_ENDPOINT_URL="http://storage.test:9000",
            S3_ACCESS_KEY="fixture",
            S3_SECRET_KEY="fixture",
            S3_BUCKET="catalogue",
            S3_PUBLIC_URL="https://media.test",
        )
    )
    data.app.dependency_overrides[avatar_storage] = lambda: storage
    identifiers = iter(UUID(int=index) for index in range(100, 200))
    monkeypatch.setattr(avatars, "uuid4", lambda: next(identifiers))
    try:
        with Stubber(storage.client) as stub:
            yield session, client, data, storage, stub
            stub.assert_no_pending_responses()
    finally:
        storage.close()


def upload_response(stub, user_id, data, extension=".png", content_type="image/png"):
    name = f"avatars/{user_id}/{UUID(int=100).hex}{extension}"
    stub.add_response("head_bucket", {}, {"Bucket": "catalogue"})
    stub.add_response(
        "put_object",
        {},
        {
            "Bucket": "catalogue",
            "Key": name,
            "Body": data,
            "ContentType": content_type,
        },
    )
    return f"https://media.test/catalogue/{name}"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "format_name,extension,content_type",
    [
        ("PNG", ".png", "image/png"),
        ("JPEG", ".jpg", "image/jpeg"),
        ("WEBP", ".webp", "image/webp"),
    ],
)
async def test_avatar_upload_detects_image_type_and_creates_profile(
    avatar_client,
    format_name,
    extension,
    content_type,
):
    session, client, data, _, stub = avatar_client
    content = image_bytes(format_name)
    expected = upload_response(stub, data.owner, content, extension, content_type)
    response = await client.post(PATH, files={"avatar": ("avatar.png", content, "text/plain")})
    assert response.status_code == 200, response.text
    assert response.json() == {"avatar": expected}
    profile = (
        await fetch(
            session,
            "SELECT avatar,nickname FROM user_profile WHERE user_id=:id",
            {"id": data.owner},
        )
    )[0]
    assert profile.avatar == expected and profile.nickname == f"user_{data.owner}"


@pytest.mark.asyncio
async def test_replacing_avatar_removes_owned_old_object_after_profile_write(avatar_client):
    session, client, data, _, stub = avatar_client
    await get_or_create_profile(session, user_id=data.owner)
    old = f"https://media.test/catalogue/avatars/{data.owner}/old.png"
    await fetch(
        session,
        "UPDATE user_profile SET avatar=:url WHERE user_id=:id RETURNING user_id",
        {"url": old, "id": data.owner},
    )
    await session.commit()
    content = image_bytes()
    expected = upload_response(stub, data.owner, content)
    stub.add_response(
        "delete_object", {}, {"Bucket": "catalogue", "Key": f"avatars/{data.owner}/old.png"}
    )
    response = await client.post(PATH, files={"avatar": ("avatar.png", content, "image/png")})
    assert response.status_code == 200 and response.json()["avatar"] == expected


@pytest.mark.asyncio
async def test_upload_failure_preserves_existing_avatar(avatar_client):
    session, client, data, _, stub = avatar_client
    await get_or_create_profile(session, user_id=data.owner)
    old = "https://external.test/avatar.png"
    await fetch(
        session,
        "UPDATE user_profile SET avatar=:url WHERE user_id=:id RETURNING user_id",
        {"url": old, "id": data.owner},
    )
    await session.commit()
    stub.add_response("head_bucket", {})
    stub.add_client_error("put_object", "AccessDenied", http_status_code=403)
    response = await client.post(PATH, files={"avatar": ("avatar.png", image_bytes(), "image/png")})
    assert response.status_code == 502 and response.json()["code"] == "users.avatar_upload_failed"
    assert (
        await fetch(
            session, "SELECT avatar FROM user_profile WHERE user_id=:id", {"id": data.owner}
        )
    )[0].avatar == old


@pytest.mark.asyncio
async def test_profile_write_failure_removes_unreferenced_upload(avatar_client, monkeypatch):
    session, client, data, _, stub = avatar_client
    await get_or_create_profile(session, user_id=data.owner)
    content = image_bytes()
    upload_response(stub, data.owner, content)
    stub.add_response(
        "delete_object",
        {},
        {
            "Bucket": "catalogue",
            "Key": f"avatars/{data.owner}/{UUID(int=100).hex}.png",
        },
    )
    real_fetch = avatars.fetch

    async def fail_update(session, query, parameters):
        if query.startswith("UPDATE user_profile"):
            raise RuntimeError("profile write failed")
        return await real_fetch(session, query, parameters)

    monkeypatch.setattr(avatars, "fetch", fail_update)
    with pytest.raises(RuntimeError, match="profile write failed"):
        await client.post(PATH, files={"avatar": ("avatar.png", content, "image/png")})
    assert (
        await fetch(
            session, "SELECT avatar FROM user_profile WHERE user_id=:id", {"id": data.owner}
        )
    )[0].avatar == ""


@pytest.mark.asyncio
async def test_lost_commit_response_keeps_the_referenced_object(avatar_client, monkeypatch):
    session, client, data, storage, stub = avatar_client
    await get_or_create_profile(session, user_id=data.owner)
    content = image_bytes()
    expected = upload_response(stub, data.owner, content)
    deleted = Mock(wraps=storage.delete_public_url)
    monkeypatch.setattr(storage, "delete_public_url", deleted)
    real_commit = session.commit
    calls = 0

    async def uncertain_commit():
        nonlocal calls
        calls += 1
        await real_commit()
        if calls == 2:
            raise RuntimeError("commit response lost")

    monkeypatch.setattr(session, "commit", uncertain_commit)
    with pytest.raises(RuntimeError, match="commit response lost"):
        await client.post(PATH, files={"avatar": ("avatar.png", content, "image/png")})
    deleted.assert_not_called()
    assert (
        await fetch(
            session, "SELECT avatar FROM user_profile WHERE user_id=:id", {"id": data.owner}
        )
    )[0].avatar == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "content,filename,message",
    [
        (b"", "empty.png", "The submitted file is empty."),
        (b"not an image", "invalid.png", avatars.INVALID_IMAGE),
        (
            image_bytes("GIF"),
            "avatar.gif",
            "Unsupported avatar content type. Allowed: image/jpeg, image/png, image/webp.",
        ),
    ],
)
async def test_invalid_images_return_existing_field_errors(
    avatar_client, content, filename, message
):
    session, client, _, _, _ = avatar_client
    response = await client.post(PATH, files={"avatar": (filename, content, "image/png")})
    assert response.status_code == 400, response.text
    assert response.json()["errors"] == {"avatar": [message]}
    assert (await fetch(session, "SELECT count(*) AS n FROM user_profile", {}))[0].n == 0


@pytest.mark.asyncio
async def test_missing_non_file_and_unsupported_request_types(avatar_client):
    _, client, _, _, _ = avatar_client
    missing = await client.post(PATH, files={"unrelated": (None, "")})
    assert missing.status_code == 400 and missing.json()["errors"] == {
        "avatar": ["No file was submitted."]
    }
    text_file = await client.post(PATH, data={"avatar": "plain text"})
    assert text_file.status_code == 400
    assert text_file.json()["errors"] == {
        "avatar": ["The submitted data was not a file. Check the encoding type on the form."]
    }
    unsupported = await client.post(PATH, json={"avatar": "plain text"})
    assert unsupported.status_code == 415
    assert unsupported.json()["detail"] == 'Unsupported media type "application/json" in request.'


@pytest.mark.asyncio
async def test_avatar_size_limit_is_applied_before_storage(avatar_client, monkeypatch):
    _, client, _, _, _ = avatar_client
    content = image_bytes()
    monkeypatch.setattr(settings, "avatar_max_upload_size", len(content) - 1)
    response = await client.post(PATH, files={"avatar": ("avatar.png", content, "image/png")})
    assert response.status_code == 400
    assert (
        "Avatar file size must be less than or equal to" in response.json()["errors"]["avatar"][0]
    )


@pytest.mark.asyncio
async def test_profile_creation_recovers_from_a_reserved_default_nickname(avatar_client):
    session, client, data, _, stub = avatar_client
    await get_or_create_profile(session, user_id=data.viewer)
    await fetch(
        session,
        "UPDATE user_profile SET nickname=:name WHERE user_id=:id RETURNING user_id",
        {"name": f"user_{data.owner}", "id": data.viewer},
    )
    await session.commit()
    content = image_bytes()
    upload_response(stub, data.owner, content)
    response = await client.post(PATH, files={"avatar": ("avatar.png", content, "image/png")})
    assert response.status_code == 200, response.text
    assert (
        await fetch(
            session, "SELECT nickname FROM user_profile WHERE user_id=:id", {"id": data.owner}
        )
    )[0].nickname == f"user_{data.owner}_1"


def test_avatar_settings_accept_existing_environment_values(monkeypatch):
    monkeypatch.setenv("AVATAR_ALLOWED_CONTENT_TYPES", " IMAGE/PNG, image/webp ")
    monkeypatch.setenv("AVATAR_MAX_UPLOAD_SIZE", "1048576")
    configured = Settings(_env_file=None)
    assert configured.avatar_allowed_content_types == ["image/png", "image/webp"]
    assert configured.avatar_max_upload_size == 1048576
