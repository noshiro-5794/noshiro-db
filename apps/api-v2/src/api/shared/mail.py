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
BRAND_NAME = "Noshiro DB"
CODE_EXPIRE_MINUTES = 5
PURPOSE_COPY = {
    "register": {
        "subject": "Your Noshiro DB sign-up code",
        "title": "Create your account",
        "intent": "Account registration",
    },
    "login": {
        "subject": "Your Noshiro DB login code",
        "title": "Log in to Noshiro DB",
        "intent": "Email code login",
    },
    "reset_password": {
        "subject": "Reset your Noshiro DB password",
        "title": "Reset your password",
        "intent": "Password reset",
    },
}


def body_text(code: str, purpose: str, site_url: str = "") -> str:
    """The plain-text body, identical to the one the old service sends."""
    copy = PURPOSE_COPY.get(purpose, PURPOSE_COPY["login"])
    return (
        f"{copy['title']}\n\n"
        f"Your {BRAND_NAME} verification code is:\n\n"
        f"{code}\n\n"
        f"This code expires in {CODE_EXPIRE_MINUTES} minutes. "
        "Do not share it with anyone.\n\n"
        f"Requested action: {copy['intent']}\n"
        f"Open Noshiro DB: {site_url}\n\n"
        "If you did not request this email, you can safely ignore it.\n"
    )


def _payload(email: str, code: str, purpose: str) -> dict[str, Any]:
    copy = PURPOSE_COPY.get(purpose, PURPOSE_COPY["login"])
    subject = copy["subject"]
    sender = os.environ.get("EMAIL_FROM", "noreply@localhost")
    text = body_text(code, purpose, os.environ.get("FRONTEND_SITE_URL", "").rstrip("/"))
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
