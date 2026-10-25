"""The state round trip, without GitHub."""

from api.contexts.access import oauth


def test_a_state_reads_back() -> None:
    state = oauth.build_state("/library", secret="s")
    body = oauth.read_state(state, secret="s")
    assert body is not None
    assert body["redirect"] == "/library"


def test_a_tampered_state_is_refused() -> None:
    state = oauth.build_state("/library", secret="s")
    assert oauth.read_state(state[:-2] + "xx", secret="s") is None


def test_a_state_signed_with_another_secret_is_refused() -> None:
    state = oauth.build_state("/library", secret="other")
    assert oauth.read_state(state, secret="s") is None


def test_an_expired_state_is_refused() -> None:
    state = oauth.build_state("/library", secret="s", nonce="n")
    body = oauth.read_state(state, secret="s", now=2**40)
    assert body is None


def test_the_url_carries_the_provider_parameters(monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_OAUTH_CLIENT_ID", "cid")
    monkeypatch.setenv("GITHUB_OAUTH_REDIRECT_URI", "https://example.test/cb")
    monkeypatch.setenv("GITHUB_OAUTH_SCOPES", "read:user")
    url = oauth.authorize_url("st")
    assert url.startswith("https://github.com/login/oauth/authorize?")
    assert "client_id=cid" in url
    assert "state=st" in url
    assert "allow_signup=true" in url
