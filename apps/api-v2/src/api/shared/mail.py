"""Verification mail.

The old service hands this to Celery and Resend; there is no queue here, so the
send happens inline and a failure is logged rather than raised — a code that was
written to the table must not be reported as a failed request.

The copy is shorter than the branded template the old service sends. That is a
cosmetic difference, recorded in `docs-parity.md`.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

RESEND_URL = "https://api.resend.com/emails"
SUBJECTS = {
    "register": "Confirm your email",
    "login": "Your sign-in code",
    "reset_password": "Reset your password",
}


def _payload(email: str, code: str, purpose: str) -> dict[str, Any]:
    subject = SUBJECTS.get(purpose, SUBJECTS["login"])
    sender = os.environ.get("EMAIL_FROM", "noreply@localhost")
    text = f"{subject}: {code}\n\nThis code expires in 10 minutes."
    return {
        "from": sender,
        "to": [email],
        "subject": subject,
        "text": text,
        "html": f"<p>{subject}: <strong>{code}</strong></p><p>This code expires in 10 minutes.</p>",
    }


async def send_verification_code(
    email: str, code: str, purpose: str, *, client: Any = None
) -> bool:
    """True when handed to the provider, False when it could not be."""
    api_key = os.environ.get("RESEND_API_KEY", "")
    if not api_key:
        logger.warning("no RESEND_API_KEY; verification mail not sent")
        return False
    transport = client or httpx.AsyncClient(timeout=10)
    try:
        response = await transport.post(
            RESEND_URL,
            json=_payload(email, code, purpose),
            headers={"Authorization": f"Bearer {api_key}"},
        )
    except httpx.HTTPError as error:
        logger.warning("verification mail failed: %s", error)
        return False
    finally:
        if client is None:
            await transport.aclose()
    if response.status_code >= 400:
        logger.warning("verification mail rejected: %s", response.status_code)
        return False
    return True
