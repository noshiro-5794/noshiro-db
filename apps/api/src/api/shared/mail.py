"""Verification mail content and Resend HTTP transport."""

from __future__ import annotations

import logging
import os
from html import escape
from importlib.resources import files
from string import Template
from typing import Any

import httpx

logger = logging.getLogger(__name__)

RESEND_URL = "https://api.resend.com/emails"
BRAND_NAME = "Noshiro DB"
CODE_EXPIRE_MINUTES = 5
BRAND_TAGLINE = "Collect · Preserve · Relive"
ACCENT_DARK = "#665792"
PURPOSE_COPY = {
    "register": {
        "subject": "Your Noshiro DB sign-up code",
        "title": "Create your account",
        "preheader": "Use this code to finish creating your Noshiro DB account.",
        "intro": "Enter this verification code to finish creating your Noshiro DB account.",
        "intent": "Account registration",
    },
    "login": {
        "subject": "Your Noshiro DB login code",
        "title": "Log in to Noshiro DB",
        "preheader": "Use this code to continue signing in. It expires in 5 minutes.",
        "intro": (
            "Enter this verification code to continue signing in to your Noshiro DB workspace."
        ),
        "intent": "Email code login",
    },
    "reset_password": {
        "subject": "Reset your Noshiro DB password",
        "title": "Reset your password",
        "preheader": "Use this code to reset your password. It expires in 5 minutes.",
        "intro": "Enter this verification code to confirm your password reset request.",
        "intent": "Password reset",
    },
}
HTML_TEMPLATE = Template(files("api.shared").joinpath("templates/verification.html").read_text())


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


def body_html(code: str, purpose: str, site_url: str = "") -> str:
    copy = PURPOSE_COPY.get(purpose, PURPOSE_COPY["login"])
    return HTML_TEMPLATE.substitute(
        safe_code=escape(code),
        site_url=escape(site_url),
        safe_brand=escape(BRAND_NAME),
        safe_title=escape(copy["title"]),
        safe_preheader=escape(copy["preheader"]),
        safe_intro=escape(copy["intro"]),
        safe_intent=escape(copy["intent"]),
        BRAND_TAGLINE=BRAND_TAGLINE,
        ACCENT_DARK=ACCENT_DARK,
        CODE_EXPIRE_MINUTES=CODE_EXPIRE_MINUTES,
    )


def _payload(email: str, code: str, purpose: str) -> dict[str, Any]:
    copy = PURPOSE_COPY.get(purpose, PURPOSE_COPY["login"])
    subject = copy["subject"]
    sender = os.environ.get("EMAIL_FROM", "noreply@localhost")
    text = body_text(code, purpose, os.environ.get("FRONTEND_SITE_URL", "").rstrip("/"))
    return {
        "from": f"{BRAND_NAME} <{sender}>",
        "to": [email],
        "subject": subject,
        "text": text,
        "html": body_html(code, purpose, os.environ.get("FRONTEND_SITE_URL", "").rstrip("/")),
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
