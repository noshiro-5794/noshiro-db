import jwt

from api.contexts.access.security import create_tokens, revoke_token, verify_password

# Produced by Django's PBKDF2PasswordHasher for "probe-pass-123". The verifier has
# to accept what the Django service stored, not merely what it writes itself.
DJANGO_HASH = (
    "pbkdf2_sha256$1500000$Ibgi6Y2w3fX1ymCf907De5$WF0+LBWdCHzvSkdfdz1xI8Ovq050QRtjvg0ERXzti4o="
)


def test_accepts_a_django_hash() -> None:
    assert verify_password(DJANGO_HASH, "probe-pass-123")


def test_rejects_a_wrong_password() -> None:
    assert not verify_password(DJANGO_HASH, "probe-pass-124")


def test_rejects_an_unknown_algorithm() -> None:
    assert not verify_password("md5$salt$digest", "probe-pass-123")


def test_tokens_carry_the_simplejwt_claims() -> None:
    access, refresh = create_tokens(
        user_id=7,
        password_hash=DJANGO_HASH,
        secret="secret",
        access_seconds=60,
        refresh_seconds=120,
    )
    decoded = jwt.decode(access, "secret", algorithms=["HS256"])
    assert decoded["token_type"] == "access"
    assert decoded["user_id"] == "7"
    assert decoded["revoke_token"] == revoke_token(DJANGO_HASH)
    assert decoded["exp"] - decoded["iat"] == 60
    assert jwt.decode(refresh, "secret", algorithms=["HS256"])["token_type"] == "refresh"
