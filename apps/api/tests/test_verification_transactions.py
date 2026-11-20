from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from api.contexts.access.api import registration
from api.contexts.presentation.fragments import fetch
from api.db import get_session
from api.main import create_app
from api.shared.problems import ProblemError
from api.worker import mail_tasks


@pytest.fixture
async def verification_runtime(integration_session, monkeypatch):
    session = integration_session

    async def sessions():
        yield session

    @asynccontextmanager
    async def scope():
        yield session
        await session.commit()

    app = create_app()
    app.dependency_overrides[get_session] = sessions
    monkeypatch.setattr(registration, "_verify_captcha", AsyncMock())
    publisher = Mock(return_value="task")
    monkeypatch.setattr(registration, "publish", publisher)
    monkeypatch.setattr(mail_tasks, "session_scope", scope)
    sender = AsyncMock(return_value=True)
    monkeypatch.setattr(mail_tasks, "send_verification_code", sender)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield session, client, publisher, sender


@pytest.mark.asyncio
async def test_request_commits_five_minute_code_before_dispatch_and_worker_delivers(
    verification_runtime,
):
    session, client, publisher, sender = verification_runtime
    response = await client.post(
        "/api/v1/auth/verification-codes/",
        json={"email": " USER@example.test ", "purpose": "register"},
    )
    assert response.status_code == 202
    assert response.json() == {"status": "accepted"}
    row = (await fetch(session, "SELECT * FROM email_verification", {}))[0]
    assert row.email == "user@example.test"
    assert len(row.code) == 6 and row.code.isdigit()
    assert 299 <= (row.expire_at - row.created_at).total_seconds() <= 300
    publisher.assert_called_once_with(
        "apps.users.tasks.email_tasks.send_verification_email", {"verification_id": row.id}
    )
    sender.assert_not_awaited()
    await mail_tasks.deliver(row.id)
    sender.assert_awaited_once_with(row.email, row.code, row.purpose)


@pytest.mark.asyncio
async def test_send_interval_is_case_insensitive_and_scoped_to_purpose(verification_runtime):
    session, client, publisher, _ = verification_runtime
    for purpose, status in [("login", 202), ("login", 429), ("reset_password", 202)]:
        response = await client.post(
            "/api/v1/auth/verification-codes/",
            json={"email": "USER@example.test", "purpose": purpose},
        )
        assert response.status_code == status
        if status == 429:
            assert response.json()["code"] == "users.email_send_too_frequent"
    assert publisher.call_count == 2
    assert (await fetch(session, "SELECT count(*) AS n FROM email_verification", {}))[0].n == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("dispatch_result", [None, RuntimeError("broker unavailable")])
async def test_dispatch_failure_is_reported_after_code_commit(
    verification_runtime, dispatch_result
):
    session, client, publisher, _ = verification_runtime
    if isinstance(dispatch_result, Exception):
        publisher.side_effect = dispatch_result
    else:
        publisher.return_value = dispatch_result
    response = await client.post(
        "/api/v1/auth/verification-codes/", json={"email": "user@example.test", "purpose": "login"}
    )
    assert response.status_code == 503
    assert response.json()["code"] == "users.email_delivery_unavailable"
    assert (await fetch(session, "SELECT count(*) AS n FROM email_verification", {}))[0].n == 1


@pytest.mark.asyncio
async def test_expired_codes_are_rejected_by_both_verification_and_delivery(verification_runtime):
    session, client, _, sender = verification_runtime
    await client.post(
        "/api/v1/auth/verification-codes/", json={"email": "user@example.test", "purpose": "login"}
    )
    row = (
        await fetch(
            session,
            "UPDATE email_verification SET expire_at=now()-interval '1 second' RETURNING id,code",
            {},
        )
    )[0]
    with pytest.raises(ProblemError) as caught:
        await registration._verify(
            session, email="user@example.test", purpose="login", code=row.code
        )
    assert caught.value.code == "users.verification_code_expired"
    await mail_tasks.deliver(row.id)
    sender.assert_not_awaited()


@pytest.mark.asyncio
async def test_attempt_limit_persists_and_used_codes_cannot_be_delivered(verification_runtime):
    session, client, _, sender = verification_runtime
    await client.post(
        "/api/v1/auth/verification-codes/", json={"email": "user@example.test", "purpose": "login"}
    )
    row = (await fetch(session, "SELECT * FROM email_verification", {}))[0]
    wrong_code = "000000" if row.code != "000000" else "111111"
    for _ in range(5):
        with pytest.raises(ProblemError):
            await registration._verify(
                session, email=row.email, purpose=row.purpose, code=wrong_code
            )
    with pytest.raises(ProblemError) as caught:
        await registration._verify(session, email=row.email, purpose=row.purpose, code=row.code)
    assert caught.value.code == "users.invalid_verification_code"
    await fetch(session, "UPDATE email_verification SET is_used=true RETURNING id", {})
    await mail_tasks.deliver(row.id)
    await mail_tasks.deliver(-1)
    sender.assert_not_awaited()


@pytest.mark.asyncio
async def test_delivery_failure_remains_retryable(verification_runtime):
    session, client, _, sender = verification_runtime
    await client.post(
        "/api/v1/auth/verification-codes/", json={"email": "user@example.test", "purpose": "login"}
    )
    row = (await fetch(session, "SELECT id FROM email_verification", {}))[0]
    sender.return_value = False
    with pytest.raises(mail_tasks.MailDeliveryError):
        await mail_tasks.deliver(row.id)
