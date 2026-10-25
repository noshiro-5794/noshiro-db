"""The GitHub authorize step.

The state is signed here rather than in Django's format. During the transition one
host routes to one service, so a state only has to come back to the service that
issued it; a round trip that starts on one and finishes on the other is the one case
this does not cover, and it is recorded rather than hidden.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any

AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
STATE_TTL = 600


def is_configured() -> bool:
    return bool(
        os.environ.get("GITHUB_OAUTH_CLIENT_ID") and os.environ.get("GITHUB_OAUTH_CLIENT_SECRET")
    )


def _sign(payload: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode(), payload, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")


def build_state(redirect: str, *, secret: str, nonce: str | None = None) -> str:
    body = {
        "nonce": nonce or secrets.token_urlsafe(24),
        "redirect": redirect,
        "issued_at": int(time.time()),
    }
    payload = json.dumps(body, separators=(",", ":")).encode()
    encoded = base64.urlsafe_b64encode(payload).decode().rstrip("=")
    return f"{encoded}.{_sign(payload, secret)}"


def read_state(state: str, *, secret: str, now: int | None = None) -> dict[str, Any] | None:
    encoded, _, signature = state.partition(".")
    if not encoded or not signature:
        return None
    try:
        payload = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
    except ValueError:
        return None
    if not hmac.compare_digest(_sign(payload, secret), signature):
        return None
    try:
        body = json.loads(payload)
    except json.JSONDecodeError:
        return None
    if not isinstance(body, dict):
        return None
    issued = body.get("issued_at")
    if not isinstance(issued, int) or (now or int(time.time())) - issued > STATE_TTL:
        return None
    return body


def authorize_url(state: str) -> str:
    from urllib.parse import urlencode

    query = urlencode(
        {
            "client_id": os.environ.get("GITHUB_OAUTH_CLIENT_ID", ""),
            "redirect_uri": os.environ.get("GITHUB_OAUTH_REDIRECT_URI", ""),
            "scope": os.environ.get("GITHUB_OAUTH_SCOPES", "read:user user:email"),
            "state": state,
            "allow_signup": "true",
        }
    )
    return f"{AUTHORIZE_URL}?{query}"
