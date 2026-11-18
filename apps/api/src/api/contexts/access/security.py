"""Password verification and token minting, compatible with the Django service.

Django stores `pbkdf2_sha256$iterations$salt$hash`; the format is checked here
rather than trusted, because an unknown algorithm must fail closed. Tokens carry
the same claims SimpleJWT writes, including the `hash_password` digest of the
password hash, so Django accepts a token minted here and the reverse.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from api.shared.problems import ProblemError

ALGORITHM = "HS256"
REFRESH = "refresh"
ACCESS = "access"


def session_claims(token: str, secret: str, *, token_type: str = ACCESS) -> dict[str, Any] | None:
    """Validate session claims before binding a user identifier to PostgreSQL."""
    if not secret:
        return None
    try:
        claims = jwt.decode(
            token,
            secret,
            algorithms=[ALGORITHM],
            options={"require": ["exp", "jti", "token_type", "user_id"]},
        )
        raw_id = claims["user_id"]
        if claims["token_type"] != token_type or isinstance(raw_id, bool):
            return None
        user_id = int(str(raw_id))
        if not 0 < user_id < 2**63:
            return None
    except (jwt.PyJWTError, ValueError, TypeError, OverflowError):
        return None
    claims["user_id"] = str(user_id)
    return claims


def verify_password(encoded: str, password: str) -> bool:
    try:
        algorithm, iterations, salt, digest = encoded.split("$", 3)
        rounds = int(iterations)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    try:
        computed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), rounds)
    except (ValueError, OverflowError):
        return False
    return hmac.compare_digest(base64.b64encode(computed), digest.encode())


def revoke_token(password_hash: str) -> str:
    return hashlib.md5(password_hash.encode()).hexdigest().upper()


def _token(*, user_id: int, password_hash: str, secret: str, token_type: str, seconds: int) -> str:
    issued = datetime.now(UTC)
    payload = {
        "token_type": token_type,
        "exp": int((issued + timedelta(seconds=seconds)).timestamp()),
        "iat": int(issued.timestamp()),
        "jti": hashlib.sha256(f"{user_id}:{issued.isoformat()}".encode()).hexdigest(),
        "user_id": str(user_id),
        "hash_password": revoke_token(password_hash),
    }
    return jwt.encode(payload, secret, algorithm=ALGORITHM)


def create_tokens(
    *, user_id: int, password_hash: str, secret: str, access_seconds: int, refresh_seconds: int
) -> tuple[str, str]:
    if not secret:
        raise ProblemError(
            status_code=503,
            detail="Authentication is not configured.",
            code="users.authentication_unavailable",
        )
    return (
        _token(
            user_id=user_id,
            password_hash=password_hash,
            secret=secret,
            token_type=ACCESS,
            seconds=access_seconds,
        ),
        _token(
            user_id=user_id,
            password_hash=password_hash,
            secret=secret,
            token_type=REFRESH,
            seconds=refresh_seconds,
        ),
    )


def hash_password(password: str, iterations: int = 1_500_000) -> str:
    """Django's format, so either service can verify a row the other wrote."""
    salt = base64.b64encode(os.urandom(12)).decode().replace("+", "").replace("/", "")[:22]
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iterations)
    return f"pbkdf2_sha256${iterations}${salt}${base64.b64encode(digest).decode()}"
