"""The verification mail, without a network."""

import pytest

from api.shared import mail


class FakeResponse:
    status_code = 200


class FakeClient:
    def __init__(self, *, fail: bool = False) -> None:
        self.payload = None
        self.headers = None
        self.fail = fail

    async def post(self, url, json=None, headers=None):
        self.payload = json
        self.headers = headers
        if self.fail:
            raise mail.httpx.HTTPError("down")
        return FakeResponse()


@pytest.fixture(autouse=True)
def key(monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "test-key")
    monkeypatch.setenv("EMAIL_FROM", "noreply@example.test")


async def test_the_mail_carries_the_code_and_the_subject() -> None:
    client = FakeClient()
    assert await mail.send_verification_code("a@example.test", "123456", "register", client=client)
    assert client.payload["to"] == ["a@example.test"]
    assert client.payload["subject"] == "Your Noshiro DB sign-up code"
    assert "123456" in client.payload["text"]
    assert client.headers["Authorization"] == "Bearer test-key"


async def test_a_missing_key_sends_nothing() -> None:
    import os

    os.environ.pop("RESEND_API_KEY", None)
    client = FakeClient()
    assert not await mail.send_verification_code("a@example.test", "123456", "login", client=client)
    assert client.payload is None


async def test_a_transport_failure_is_not_raised() -> None:
    client = FakeClient(fail=True)
    assert not await mail.send_verification_code("a@example.test", "123456", "login", client=client)


def test_the_text_body_matches_the_old_service() -> None:
    from textwrap import dedent

    expected = dedent(
        """\
        Log in to Noshiro DB

        Your Noshiro DB verification code is:

        123456

        This code expires in 5 minutes. Do not share it with anyone.

        Requested action: Email code login
        Open Noshiro DB: https://noshiro.moe

        If you did not request this email, you can safely ignore it.
        """
    )
    assert mail.body_text("123456", "login", "https://noshiro.moe") == expected


def test_html_preserves_brand_template_and_escapes_dynamic_values():
    html = mail.body_html("<123&>", "register", "https://example.test/?a=1&b=2")
    assert "<!doctype html>" in html
    assert "&lt;123&amp;&gt;" in html
    assert "https://example.test/?a=1&amp;b=2" in html
    assert "Create your account" in html
    assert "5 minutes" in html
    assert "10 minutes" not in html


def test_worker_entry_preserves_queued_verification_id(monkeypatch):
    from unittest.mock import AsyncMock

    from api.worker import mail_tasks

    deliver = AsyncMock()
    monkeypatch.setattr(mail_tasks, "deliver", deliver)
    execution = mail_tasks.send_verification_email.apply(kwargs={"verification_id": 17})
    assert execution.get() is None
    deliver.assert_awaited_once_with(17)


def test_application_registers_each_method_and_path_once():
    from fastapi.routing import APIRoute

    from api.main import create_app

    routes = [
        (method, route.path)
        for route in create_app().routes
        if isinstance(route, APIRoute)
        for method in route.methods
    ]
    assert len(routes) == len(set(routes))
