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
