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
from datetime import UTC, datetime, timedelta

import jwt

ALGORITHM = "HS256"
REFRESH = "refresh"
ACCESS = "access"


def verify_password(encoded: str, password: str) -> bool:
    try:
        algorithm, iterations, salt, digest = encoded.split("$", 3)
        rounds = int(iterations)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    computed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), rounds)
    return hmac.compare_digest(base64.b64encode(computed).decode(), digest)


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
